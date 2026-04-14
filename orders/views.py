from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.views.generic import ListView, DetailView
from django.contrib import messages
from django.http import HttpResponse
from .models import Order, OrderItem, OrderStatusHistory
from parties.models import Party
from inventory.models import DesignType, Stock
from ledger.models import Transaction, PartyBalance
from django.db import transaction
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import timedelta
from decimal import Decimal
from core.models import Notification
User = get_user_model()
from reportlab.pdfgen import canvas
from io import BytesIO

class AdminAccountantMixin(UserPassesTestMixin):
    def test_func(self):
        return self.request.user.is_admin() or self.request.user.is_accountant()

class WarehouseManagerMixin(UserPassesTestMixin):
    def test_func(self):
        return self.request.user.is_warehouse_manager() or self.request.user.is_admin()

class OrderListView(LoginRequiredMixin, ListView):
    model = Order
    template_name = 'orders/order_list.html'
    context_object_name = 'orders'
    paginate_by = 20

    def get_queryset(self):
        queryset = super().get_queryset().select_related('party', 'created_by', 'delivery_partner').prefetch_related('items', 'items__design_type', 'status_history').order_by('-created_at')
        status = self.request.GET.get('status')
        if status:
            queryset = queryset.filter(status=status)
        
        # Date range filtering
        start_date = self.request.GET.get('start_date')
        end_date = self.request.GET.get('end_date')
        if start_date:
            queryset = queryset.filter(created_at__date__gte=start_date)
        if end_date:
            queryset = queryset.filter(created_at__date__lte=end_date)
            
        # Role-based filtering
        if self.request.user.is_warehouse_manager():
            queryset = queryset.filter(status__in=['created', 'cutting', 'ready'])
        elif self.request.user.is_delivery_person():
            queryset = queryset.filter(delivery_partner=self.request.user, status__in=['assigned', 'out_for_delivery'])
        
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        for order in context.get('orders', []):
            assigned_history = None
            for h in order.status_history.all():
                if h.status == 'assigned' and (assigned_history is None or h.timestamp > assigned_history.timestamp):
                    assigned_history = h
            order.assigned_at = assigned_history.timestamp if assigned_history else None
        return context

class OrderDetailView(LoginRequiredMixin, DetailView):
    model = Order
    template_name = 'orders/order_detail.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        assigned_history = self.object.status_history.filter(status='assigned').select_related('updated_by').order_by('-timestamp').first()
        context['assigned_history'] = assigned_history
        if self.object.status == 'ready' and (self.request.user.is_admin() or self.request.user.is_accountant()):
            context['delivery_partners'] = User.objects.filter(role='delivery_person')
        return context

@login_required
@transaction.atomic
def order_create(request):
    if not (request.user.is_admin() or request.user.is_accountant()):
        return redirect('dashboard')
    if request.method == 'POST':
        party_id = request.POST.get('party')
        delivery_address = request.POST.get('delivery_address')
        design_type_ids = request.POST.getlist('design_type')
        quantities = request.POST.getlist('quantity')
        prices = request.POST.getlist('price')
        gst_percent = Decimal(request.POST.get('gst_percent', '0'))

        party = get_object_or_404(Party, id=party_id)
        
        # We wrap in another atomic block just in case, but the function is already decorated
        order = Order.objects.create(
            party=party,
            delivery_address=delivery_address,
            created_by=request.user
        )

        total_amount = Decimal('0.00')
        for dt_id, qty, price in zip(design_type_ids, quantities, prices):
            if not dt_id: continue
            dt = get_object_or_404(DesignType, id=dt_id)
            qty = Decimal(qty)
            
            # Stock check
            stock, created = Stock.objects.get_or_create(design_type=dt)
            if stock.quantity < qty:
                # Rollback is automatic due to transaction.atomic() decorator
                messages.error(request, f"Unable to place, update stock from inventory! (Insufficient stock for {dt.name}. Available: {stock.quantity})")
                transaction.set_rollback(True)
                return redirect('order_create')
                
            price = Decimal(price) if price else Decimal('0.00')
            item_total = qty * price
            OrderItem.objects.create(
                order=order,
                design_type=dt,
                quantity=qty,
                price_per_meter=price,
                total_price=item_total
            )
            total_amount += item_total

        gst_amount = (total_amount * gst_percent) / Decimal('100.00')
        grand_total = total_amount + gst_amount

        order.total_amount = total_amount
        order.gst_amount = gst_amount
        order.grand_total = grand_total
        order.balance_amount = grand_total
        order.save()

        # Update Ledger only if grand_total > 0
        if grand_total > 0:
            Transaction.objects.create(
                party=party,
                transaction_type='sale',
                amount=grand_total,
                debit=grand_total,
                order=order,
                description=f"Order {order.invoice_number} created"
            )
            
            # Update Party Balance
            balance, created = PartyBalance.objects.get_or_create(party=party)
            balance.total_debit += grand_total
            balance.current_balance += grand_total
            balance.save()

        # Notification for Warehouse Managers
        msg = f"New Order {order.invoice_number} received for cutting."
        link = f"/orders/{order.id}/"
        cutters = User.objects.filter(role='warehouse_manager')
        for cutter in cutters:
            Notification.objects.create(user=cutter, message=msg, link=link)

        messages.success(request, f"Order {order.invoice_number} created successfully")
        return redirect('order_detail', pk=order.pk)

    parties = Party.objects.all()
    from inventory.models import Collection
    collections = Collection.objects.all()
    selected_party_id = request.GET.get('party')
    
    return render(request, 'orders/order_form.html', {
        'parties': parties,
        'collections': collections,
        'selected_party_id': selected_party_id
    })

@login_required
def order_status_update(request, pk, status):
    if not (request.user.is_admin() or request.user.is_accountant() or request.user.is_warehouse_manager() or request.user.is_delivery_person()):
        return redirect('dashboard')
    
    order = get_object_or_404(Order, pk=pk)
    
    if status == 'assigned' and not (request.user.is_admin() or request.user.is_accountant()):
        messages.error(request, "Only Admin/Accountant can assign delivery.")
        if request.user.is_warehouse_manager():
            return redirect('warehouse_dashboard')
        return redirect('order_detail', pk=pk)

    # Transition to 'ready' (Cutter finished)
    if status == 'ready' and request.user.is_warehouse_manager():
        if order.transition_to('ready', request.user):
            # Notify Accountant/Admin for delivery assignment
            msg = f"Order {order.invoice_number} is ready. Please assign delivery."
            link = f"/orders/{order.id}/"
            assigners = User.objects.filter(role__in=['admin', 'accountant', 'superadmin'])
            for assigner in assigners:
                Notification.objects.create(user=assigner, message=msg, link=link)
            messages.success(request, f"Order {order.invoice_number} marked as Ready. Admin/Accountant notified.")
            return redirect('warehouse_dashboard')

    # Transition to 'assigned' (Accountant assigns delivery)
    if status == 'assigned' and (request.user.is_admin() or request.user.is_accountant()):
        delivery_choice = (request.POST.get('delivery_choice') or '').strip()
        dp_id = (request.POST.get('delivery_partner_id') or '').strip()
        method = (request.POST.get('delivery_method') or '').strip()
        ref_no = request.POST.get('delivery_reference_number')

        if delivery_choice:
            if ':' in delivery_choice:
                method, dp_id = delivery_choice.split(':', 1)
                method = method.strip()
                dp_id = dp_id.strip()
            else:
                method = delivery_choice
        
        valid_methods = {choice[0] for choice in Order.DELIVERY_METHOD_CHOICES}
        if not method or method not in valid_methods:
            messages.error(request, "Please select a valid delivery option.")
            return redirect('order_detail', pk=order.pk)

        if not dp_id:
            messages.error(request, "Please select a delivery person.")
            return redirect('order_detail', pk=order.pk)

        dp = get_object_or_404(User, id=dp_id)
        order.delivery_partner = dp
        order.delivery_method = method
        order.delivery_reference_number = ref_no
        if order.transition_to('assigned', request.user):
            msg = f"New delivery task assigned for Order {order.invoice_number}."
            link = f"/orders/{order.id}/"
            Notification.objects.create(user=dp, message=msg, link=link)
            messages.success(request, f"Order {order.invoice_number} assigned to {dp.username}")
        else:
            messages.error(request, "Invalid status transition")
        return redirect('order_detail', pk=order.pk)

    if order.transition_to(status, request.user):
        messages.success(request, f"Order status updated to {status}")
    else:
        messages.error(request, "Invalid status transition")
    
    if request.user.is_warehouse_manager():
        return redirect('warehouse_dashboard')
    elif request.user.is_delivery_person():
        return redirect('delivery_dashboard')
    
    return redirect('order_detail', pk=pk)

# Dashboards
@login_required
def warehouse_dashboard(request):
    if not request.user.is_warehouse_manager() and not request.user.is_admin():
        return redirect('dashboard')
    
    # Cutting tasks
    cutting_tasks = Order.objects.filter(status__in=['created', 'cutting']).order_by('-created_at')
    # Ready for dispatch
    ready_orders = Order.objects.filter(status='ready')
    delivery_partners = User.objects.filter(role='delivery_person')
    
    return render(request, 'orders/dashboard_warehouse.html', {
        'cutting_tasks': cutting_tasks,
        'ready_orders': ready_orders,
        'delivery_partners': delivery_partners
    })

@login_required
def delivery_dashboard(request):
    if not request.user.is_delivery_person() and not request.user.is_admin():
        return redirect('dashboard')
    assigned_orders = list(
        Order.objects.filter(delivery_partner=request.user, status__in=['assigned', 'out_for_delivery'])
        .select_related('party')
    )
    order_ids = [o.id for o in assigned_orders]
    if order_ids:
        histories = (
            OrderStatusHistory.objects.filter(order_id__in=order_ids, status='assigned')
            .select_related('updated_by')
            .order_by('-timestamp')
        )
        latest_by_order_id = {}
        for h in histories:
            if h.order_id not in latest_by_order_id:
                latest_by_order_id[h.order_id] = h
    else:
        latest_by_order_id = {}

    for o in assigned_orders:
        h = latest_by_order_id.get(o.id)
        o.assigned_at = h.timestamp if h else None
        o.assigned_by = h.updated_by.username if h and h.updated_by else None

    return render(request, 'orders/dashboard_delivery.html', {'orders': assigned_orders})

@login_required
def delivery_challan_pdf(request, pk):
    order = get_object_or_404(Order, pk=pk)
    # RBAC: Delivery, Accountant, Admin can see
    if not (request.user.is_admin() or request.user.is_accountant() or request.user.is_delivery_person()):
        return redirect('dashboard')

    buffer = BytesIO()
    p = canvas.Canvas(buffer)
    
    p.setFont("Helvetica-Bold", 16)
    p.drawString(100, 800, f"DELIVERY CHALLAN: {order.invoice_number}")
    
    p.setFont("Helvetica", 12)
    p.drawString(100, 780, f"Date: {order.created_at.strftime('%Y-%m-%d')}")
    p.drawString(100, 760, f"Customer: {order.party.name}")
    if hasattr(order.party, 'alias') and order.party.alias:
        p.drawString(100, 740, f"Alias: {order.party.alias}")
    p.drawString(100, 720, f"Address: {order.delivery_address}")
    
    p.line(50, 700, 550, 700)
    p.setFont("Helvetica-Bold", 10)
    p.drawString(50, 685, "SR")
    p.drawString(100, 685, "ITEM NAME")
    p.drawRightString(350, 685, "QTY")
    p.line(50, 680, 550, 680)
    
    y = 665
    for i, item in enumerate(order.items.all(), 1):
        p.setFont("Helvetica", 10)
        p.drawString(50, y, str(i))
        item_name = item.design_type.name if item.design_type else "N/A"
        p.drawString(100, y, item_name)
        unit = item.design_type.unit if item.design_type else ""
        p.drawRightString(350, y, f"{item.quantity} {unit}")
        y -= 20
        if y < 50:
            p.showPage()
            y = 800
            
    p.line(50, y, 550, y)
    y -= 20
    p.drawString(100, y, f"Total Amount to Collect: INR {order.balance_amount}")
    
    p.showPage()
    p.save()
    
    buffer.seek(0)
    return HttpResponse(buffer, content_type='application/pdf')

# Delivery Actions
@login_required
def order_pickup(request, pk):
    order = get_object_or_404(Order, pk=pk, delivery_partner=request.user)
    order.transition_to('out_for_delivery', request.user)
    messages.success(request, f"Order {order.invoice_number} picked up")
    return redirect('delivery_dashboard')

@login_required
def order_start_delivery(request, pk):
    # This is just for UI status, already handled by pickup or can be separate
    return redirect('delivery_dashboard')

@login_required
def order_mark_delivered(request, pk):
    # Get order assigned to user OR admin
    if request.user.is_admin():
        order = get_object_or_404(Order, pk=pk)
    else:
        order = get_object_or_404(Order, pk=pk, delivery_partner=request.user)
    
    # Prevent multiple delivery marking - stricter check
    if order.status in ['delivered', 'paid']:
        messages.warning(request, f"Order {order.invoice_number} is already marked as {order.status.title()}. No further updates allowed.")
        return redirect('delivery_dashboard')

    if request.method == 'POST':
        with transaction.atomic():
            # Refresh order from DB to ensure status hasn't changed in another thread
            order = Order.objects.select_for_update().get(pk=pk)
            if order.status in ['delivered', 'paid']:
                messages.error(request, "Order status was updated by someone else.")
                return redirect('delivery_dashboard')

            amount_raw = (request.POST.get('amount') or '0').strip()
            try:
                amount = Decimal(amount_raw or '0')
            except Exception:
                messages.error(request, "Invalid amount.")
                return redirect('order_mark_delivered', pk=order.pk)

            if amount < 0:
                messages.error(request, "Amount cannot be negative.")
                return redirect('order_mark_delivered', pk=order.pk)

            mode = request.POST.get('mode')
            transaction_id = request.POST.get('transaction_id')
            
            from payments.models import Payment
            payment = Payment.objects.create(
                order=order,
                amount=amount,
                mode=mode,
                transaction_id=transaction_id,
                recorded_by=request.user
            )
            
            order.balance_amount -= amount
            if order.balance_amount < 0:
                order.balance_amount = Decimal('0.00')
            
            is_fully_paid = order.balance_amount <= 0
            notes = f"Payment of {amount} via {(mode or '').upper()} recorded."
            if order.status != 'out_for_delivery':
                messages.error(request, "Order must be Out for Delivery before it can be marked delivered.")
                transaction.set_rollback(True)
                return redirect('delivery_dashboard')

            if not order.transition_to('delivered', request.user, notes=notes):
                messages.error(request, "Invalid status transition")
                transaction.set_rollback(True)
                return redirect('delivery_dashboard')

            if is_fully_paid:
                order.transition_to('paid', request.user, notes=notes)
            
            # Update Ledger for payment
            Transaction.objects.create(
                party=order.party,
                transaction_type='payment',
                amount=amount,
                credit=amount,
                order=order,
                payment=payment,
                description=f"Payment for order {order.invoice_number}"
            )
            
            # Update Balance
            balance, created = PartyBalance.objects.get_or_create(party=order.party)
            balance.total_credit += amount
            balance.current_balance -= amount
            balance.save()

            messages.success(request, f"Order {order.invoice_number} marked as {'Paid' if is_fully_paid else 'Delivered'}.")
            return redirect('delivery_dashboard')
    
    from shop_config.models import ShopConfiguration
    shop_config = ShopConfiguration.objects.first()
    upi_url = shop_config.build_upi_url(amount=order.balance_amount, note=f"Invoice {order.invoice_number}") if shop_config else None
    return render(request, 'orders/payment_form.html', {'order': order, 'upi_url': upi_url})

@login_required
def generate_invoice_pdf(request, pk):
    if not (request.user.is_admin() or request.user.is_accountant()):
        return redirect('dashboard')
    order = get_object_or_404(Order, pk=pk)
    buffer = BytesIO()
    p = canvas.Canvas(buffer)
    
    p.setFont("Helvetica-Bold", 16)
    p.drawString(100, 800, f"INVOICE: {order.invoice_number}")
    
    p.setFont("Helvetica", 12)
    p.drawString(100, 780, f"Date: {order.created_at.strftime('%Y-%m-%d')}")
    p.drawString(100, 760, f"Customer: {order.party.name}")
    p.drawString(100, 740, f"Address: {order.delivery_address}")
    
    p.line(50, 720, 550, 720)
    p.setFont("Helvetica-Bold", 10)
    p.drawString(50, 705, "SR")
    p.drawString(100, 705, "ITEM DESCRIPTION")
    p.drawRightString(350, 705, "QTY")
    p.drawRightString(450, 705, "RATE")
    p.drawRightString(550, 705, "AMOUNT")
    p.line(50, 700, 550, 700)
    
    y = 680
    p.setFont("Helvetica", 10)
    for i, item in enumerate(order.items.all(), 1):
        p.drawString(50, y, str(i))
        item_name = item.design_type.name if item.design_type else "N/A"
        p.drawString(100, y, item_name)
        unit = item.design_type.unit if item.design_type else ""
        p.drawRightString(350, y, f"{item.quantity} {unit}")
        p.drawRightString(450, y, f"{item.price_per_meter}")
        p.drawRightString(550, y, f"{item.total_price}")
        y -= 20
        if y < 100: # Simple pagination
            p.showPage()
            y = 800
        
    p.line(50, y+10, 550, y+10)
    y -= 10
    
    # Summary Table
    p.setFont("Helvetica", 11)
    p.drawString(380, y, "Sub Total:")
    p.drawRightString(550, y, f"INR {order.total_amount}")
    y -= 20
    p.drawString(380, y, "GST:")
    p.drawRightString(550, y, f"INR {order.gst_amount}")
    y -= 25
    
    p.setStrokeColorRGB(0, 0, 0)
    p.setLineWidth(1.5)
    p.line(380, y+20, 550, y+20)
    p.setFont("Helvetica-Bold", 13)
    p.drawString(380, y, "GRAND TOTAL:")
    p.drawRightString(550, y, f"INR {order.grand_total}")
    
    p.setLineWidth(1)
    p.line(50, 50, 550, 50)
    p.setFont("Helvetica-Oblique", 8)
    p.drawString(50, 40, "This is a computer generated invoice.")
    
    p.showPage()
    p.save()
    
    buffer.seek(0)
    return HttpResponse(buffer, content_type='application/pdf')
