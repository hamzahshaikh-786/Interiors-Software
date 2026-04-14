from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth import logout
from django.contrib import messages
from django.db import models
from orders.models import Order
from parties.models import Party
from inventory.models import Stock
from ledger.models import PartyBalance
from django.utils import timezone
from datetime import timedelta
from .models import Notification

@login_required
def dashboard(request):
    user = request.user
    context = {}

    if user.is_admin() or user.is_accountant():
        context['total_orders'] = Order.objects.count()
        context['pending_orders'] = Order.objects.filter(status='created').count()
        context['total_parties'] = Party.objects.count()
        context['low_stock_items'] = Stock.objects.filter(quantity__lte=models.F('low_stock_threshold'))
        
        # Monthly Sales
        month_start = timezone.now().replace(day=1, hour=0, minute=0, second=0)
        context['monthly_sales'] = Order.objects.filter(created_at__gte=month_start).aggregate(models.Sum('grand_total'))['grand_total__sum'] or 0.00
        
        # Outstanding Payments (Separated)
        balances = PartyBalance.objects.all()
        context['overdue_amount'] = balances.filter(current_balance__gt=0).aggregate(models.Sum('current_balance'))['current_balance__sum'] or 0.00
        context['advance_amount'] = abs(balances.filter(current_balance__lt=0).aggregate(models.Sum('current_balance'))['current_balance__sum'] or 0.00)
        
        # Recent Orders
        context['recent_orders'] = Order.objects.all().order_by('-created_at')[:5]
        
        # Top Customers
        context['top_customers'] = PartyBalance.objects.all().order_by('-total_debit')[:5]

        return render(request, 'core/dashboard_admin.html', context)

    elif user.is_warehouse_manager():
        return redirect('warehouse_dashboard')

    elif user.is_delivery_person():
        return redirect('delivery_dashboard')

    elif user.is_marketing_person():
        return redirect('party_list')

    return render(request, 'core/dashboard.html', context)

@login_required
def mark_notification_seen(request, pk):
    notification = get_object_or_404(Notification, pk=pk, user=request.user)
    notification.is_seen = True
    notification.save()
    if notification.link:
        return redirect(notification.link)
    return redirect('dashboard')

@login_required
def analytics_dashboard(request):
    if not request.user.is_admin() and not request.user.is_accountant():
        return redirect('dashboard')
        
    now = timezone.now()
    last_7_days = now - timedelta(days=7)
    last_15_days = now - timedelta(days=15)
    last_30_days = now - timedelta(days=30)

    # Inactive Customers
    inactive_7 = Party.objects.exclude(orders__created_at__gte=last_7_days).distinct()
    inactive_15 = Party.objects.exclude(orders__created_at__gte=last_15_days).distinct()
    inactive_30 = Party.objects.exclude(orders__created_at__gte=last_30_days).distinct()

    # Sales Trends (Monthly)
    month_trends = Order.objects.filter(created_at__gte=now - timedelta(days=365))\
        .annotate(month=models.functions.ExtractMonth('created_at'), year=models.functions.ExtractYear('created_at'))\
        .values('year', 'month')\
        .annotate(total=models.Sum('grand_total'))\
        .order_by('year', 'month')

    # Order Status Distribution
    status_dist = Order.objects.values('status').annotate(count=models.Count('id'))
    
    context = {
        'inactive_7': inactive_7,
        'inactive_15': inactive_15,
        'inactive_30': inactive_30,
        
        'pending_payments': Order.objects.filter(balance_amount__gt=0),
        'overdue_payments': Order.objects.filter(balance_amount__gt=0, created_at__lt=last_30_days),
        
        'high_value_clients': PartyBalance.objects.order_by('-total_debit')[:10],
        
        'chart_data': {
            'labels': [timezone.datetime(item['year'], item['month'], 1).strftime('%b %Y') for item in month_trends],
            'values': [float(item['total']) for item in month_trends]
        },
        'status_data': {
            'labels': [item['status'].replace('_', ' ').title() for item in status_dist],
            'values': [item['count'] for item in status_dist]
        }
    }
    
    return render(request, 'core/analytics.html', context)

@login_required
def daybook(request):
    if not (request.user.is_admin() or request.user.is_accountant()):
        return redirect('dashboard')
        
    date_str = request.GET.get('date')
    if date_str:
        selected_date = timezone.datetime.strptime(date_str, '%Y-%m-%d').date()
    else:
        selected_date = timezone.now().date()
        
    start_time = timezone.make_aware(timezone.datetime.combine(selected_date, timezone.datetime.min.time()))
    end_time = timezone.make_aware(timezone.datetime.combine(selected_date, timezone.datetime.max.time()))
    
    orders = Order.objects.filter(created_at__range=(start_time, end_time)).select_related('party')
    
    # Financial summary for the day
    total_sales = orders.aggregate(models.Sum('grand_total'))['grand_total__sum'] or 0.00
    
    # Payments received today
    from payments.models import Payment
    payments = Payment.objects.filter(timestamp__range=(start_time, end_time)).select_related('order', 'order__party')
    total_payments = payments.aggregate(models.Sum('amount'))['amount__sum'] or 0.00
    
    context = {
        'selected_date': selected_date,
        'orders': orders,
        'payments': payments,
        'total_sales': total_sales,
        'total_payments': total_payments,
    }
    return render(request, 'core/daybook.html', context)

@login_required
def logout_view(request):
    logout(request)
    messages.success(request, "Logged out successfully")
    return redirect('login')
