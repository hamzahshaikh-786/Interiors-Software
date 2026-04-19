from django.shortcuts import render, redirect, get_object_or_404
from django.views.generic import ListView, CreateView, UpdateView, DeleteView
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.urls import reverse_lazy
from django.contrib import messages
from .models import Collection, DesignType, Stock, Purchaser, PurchaseEntry, PurchaseItem
from users.models import User
from django import forms
from django.core.exceptions import ValidationError

class AdminAccountantMixin(UserPassesTestMixin):
    def test_func(self):
        return self.request.user.is_admin() or self.request.user.is_accountant()

class WarehouseManagerMixin(UserPassesTestMixin):
    def test_func(self):
        return self.request.user.is_warehouse_manager() or self.request.user.is_admin()

from django.db.models import Q
from django.db import transaction
from core.models import Notification

class StockListView(LoginRequiredMixin, ListView):
    model = Stock
    template_name = 'inventory/stock_list.html'
    context_object_name = 'stocks'

    def get_queryset(self):
        queryset = super().get_queryset().select_related('design_type', 'design_type__collection')
        q = self.request.GET.get('q')
        if q:
            queryset = queryset.filter(
                Q(design_type__name__icontains=q) |
                Q(design_type__alias1__icontains=q) |
                Q(design_type__alias2__icontains=q) |
                Q(design_type__alias3__icontains=q) |
                Q(design_type__alias4__icontains=q) |
                Q(design_type__alias5__icontains=q) |
                Q(design_type__collection__name__icontains=q)
            )
        collection_id = self.request.GET.get('collection')
        if collection_id:
            queryset = queryset.filter(design_type__collection_id=collection_id)
        return queryset

    def get_initial(self):
        initial = super().get_initial()
        collection_id = self.request.GET.get('collection')
        if collection_id:
            initial['collection'] = collection_id
        return initial

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['collections'] = Collection.objects.prefetch_related('designs').all()
        return context

# Collection Views
class CollectionListView(LoginRequiredMixin, AdminAccountantMixin, ListView):
    model = Collection
    template_name = 'inventory/collection_list.html'
    context_object_name = 'collections'

class CollectionCreateView(LoginRequiredMixin, AdminAccountantMixin, CreateView):
    model = Collection
    fields = ['name', 'description']
    template_name = 'inventory/collection_form.html'
    success_url = reverse_lazy('collection_list')

class CollectionUpdateView(LoginRequiredMixin, AdminAccountantMixin, UpdateView):
    model = Collection
    fields = ['name', 'description']
    template_name = 'inventory/collection_form.html'
    success_url = reverse_lazy('collection_list')

class CollectionDeleteView(LoginRequiredMixin, AdminAccountantMixin, DeleteView):
    model = Collection
    template_name = 'inventory/collection_confirm_delete.html'
    success_url = reverse_lazy('collection_list')

# DesignType Views
class DesignTypeForm(forms.ModelForm):
    class Meta:
        model = DesignType
        fields = ['collection', 'name', 'alias1', 'alias2', 'alias3', 'alias4', 'alias5', 'description', 'unit', 'default_price']

    def clean(self):
        cleaned_data = super().clean()
        collection = cleaned_data.get('collection')
        name = (cleaned_data.get('name') or '').strip()
        if collection and name:
            exists = DesignType.objects.filter(collection=collection, name__iexact=name).exclude(pk=self.instance.pk).exists()
            if exists:
                raise ValidationError({'name': 'A design with this name already exists in the selected collection.'})
        cleaned_data['name'] = name
        return cleaned_data

class DesignTypeCreateView(LoginRequiredMixin, AdminAccountantMixin, CreateView):
    model = DesignType
    form_class = DesignTypeForm
    template_name = 'inventory/designtype_form.html'
    success_url = reverse_lazy('stock_list')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['collections'] = Collection.objects.all()
        return context

    def form_valid(self, form):
        response = super().form_valid(form)
        Stock.objects.get_or_create(design_type=self.object)
        messages.success(self.request, f"Design type {self.object.name} added successfully")
        return response

class DesignTypeUpdateView(LoginRequiredMixin, AdminAccountantMixin, UpdateView):
    model = DesignType
    form_class = DesignTypeForm
    template_name = 'inventory/designtype_form.html'
    success_url = reverse_lazy('stock_list')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['collections'] = Collection.objects.all()
        return context

class DesignTypeDeleteView(LoginRequiredMixin, AdminAccountantMixin, DeleteView):
    model = DesignType
    template_name = 'inventory/designtype_confirm_delete.html'
    success_url = reverse_lazy('stock_list')

# Stock Update
class StockUpdateView(LoginRequiredMixin, AdminAccountantMixin, UpdateView):
    model = Stock
    fields = ['quantity', 'low_stock_threshold']
    template_name = 'inventory/stock_form.html'
    success_url = reverse_lazy('stock_list')

    def form_valid(self, form):
        messages.success(self.request, f"Stock for {self.object.design_type.name} updated successfully")
        return super().form_valid(form)

# Purchaser CRUD
class PurchaserListView(LoginRequiredMixin, AdminAccountantMixin, ListView):
    model = Purchaser
    template_name = 'inventory/purchaser_list.html'
    context_object_name = 'purchasers'

class PurchaserCreateView(LoginRequiredMixin, AdminAccountantMixin, CreateView):
    model = Purchaser
    fields = ['name', 'phone', 'address']
    template_name = 'inventory/purchaser_form.html'
    success_url = reverse_lazy('purchaser_list')

class PurchaserUpdateView(LoginRequiredMixin, AdminAccountantMixin, UpdateView):
    model = Purchaser
    fields = ['name', 'phone', 'address']
    template_name = 'inventory/purchaser_form.html'
    success_url = reverse_lazy('purchaser_list')

class PurchaserDeleteView(LoginRequiredMixin, AdminAccountantMixin, DeleteView):
    model = Purchaser
    template_name = 'inventory/purchaser_confirm_delete.html'
    success_url = reverse_lazy('purchaser_list')

# Purchase Entry (Warehouse Manager & Accountant)
@login_required
def purchase_entry_create(request):
    if not (request.user.is_warehouse_manager() or request.user.is_accountant() or request.user.is_admin()):
        return redirect('dashboard')
    
    if request.method == 'POST':
        purchaser_id = request.POST.get('purchaser')
        
        # Multiple items handling
        design_ids = request.POST.getlist('design_type')
        quantities = request.POST.getlist('quantity')
        conditions = request.POST.getlist('material_condition')
        colour_matches = request.POST.getlist('design_colour_match')
        tagging_dones = request.POST.getlist('tagging_done')
        vias = request.POST.getlist('via')
        
        purchaser = get_object_or_404(Purchaser, id=purchaser_id)
        
        with transaction.atomic():
            purchase = PurchaseEntry.objects.create(
                purchaser=purchaser,
                created_by=request.user,
                reference_bill_number=""
            )
            
            for d_id, qty, cond, match, tag, via in zip(design_ids, quantities, conditions, colour_matches, tagging_dones, vias):
                if not d_id: continue
                design = get_object_or_404(DesignType, id=d_id)
                PurchaseItem.objects.create(
                    purchase_entry=purchase,
                    design_type=design,
                    quantity=qty,
                    material_condition=cond,
                    design_colour_match=match,
                    tagging_done=tag == 'yes',
                    via=via
                )
            
            # Create notifications for Admin/Accountant
            review_url = f"/inventory/purchases/{purchase.id}/approve/"
            msg = f"New Purchase Entry from {request.user.username} requires review."
            approvers = User.objects.filter(role__in=['admin', 'accountant', 'superadmin'])
            for approver in approvers:
                Notification.objects.create(user=approver, message=msg, link=review_url)
        
        messages.success(request, f"Purchase entry submitted for approval")
        return redirect('purchase_list')

    purchasers = Purchaser.objects.all()
    collections = Collection.objects.all()
    return render(request, 'inventory/purchase_form.html', {
        'purchasers': purchasers,
        'collections': collections
    })

@login_required
def purchase_list(request):
    if request.user.is_accountant() or request.user.is_admin():
        purchases = PurchaseEntry.objects.all().order_by('-created_at')
    elif request.user.is_warehouse_manager():
        purchases = PurchaseEntry.objects.filter(created_by=request.user).order_by('-created_at')
    else:
        return redirect('dashboard')

    purchases = purchases.select_related('purchaser', 'created_by').prefetch_related('items', 'items__design_type')
    q = (request.GET.get('q') or '').strip()
    if q:
        purchases = purchases.filter(
            Q(reference_bill_number__icontains=q) |
            Q(purchaser__name__icontains=q) |
            Q(created_by__username__icontains=q) |
            Q(items__design_type__name__icontains=q) |
            Q(items__design_type__alias1__icontains=q) |
            Q(items__design_type__alias2__icontains=q) |
            Q(items__design_type__alias3__icontains=q) |
            Q(items__design_type__alias4__icontains=q) |
            Q(items__design_type__alias5__icontains=q)
        ).distinct()

    status = (request.GET.get('status') or '').strip()
    if status in {'pending', 'approved', 'rejected'}:
        purchases = purchases.filter(status=status)
    
    return render(request, 'inventory/purchase_list.html', {'purchases': purchases})

@login_required
def purchase_approve(request, pk):
    if not (request.user.is_accountant() or request.user.is_admin()):
        return redirect('dashboard')
    
    purchase = get_object_or_404(PurchaseEntry, pk=pk)
    if request.method == 'POST':
        action = request.POST.get('action')
        
        if action == 'process_items':
            item_ids = request.POST.getlist('item_id')
            approved_ids = request.POST.getlist('approved_items')
            ref_bill = request.POST.get('reference_bill_number')
            
            if not ref_bill:
                messages.error(request, "Reference Bill Number is required.")
                return redirect('purchase_approve', pk=pk)
            
            with transaction.atomic():
                purchase.reference_bill_number = ref_bill
                
                for item in purchase.items.all():
                    if str(item.id) in approved_ids:
                        item.status = 'approved'
                        # Increase stock
                        stock, created = Stock.objects.get_or_create(design_type=item.design_type)
                        stock.quantity += item.quantity
                        stock.save()
                    else:
                        item.status = 'rejected'
                    item.save()
                
                # Update overall purchase status
                if approved_ids:
                    purchase.status = 'approved'
                else:
                    purchase.status = 'rejected'
                
                purchase.approved_by = request.user
                purchase.save()
                
                # Notify the creator
                msg = f"Your Purchase Entry (ID: {purchase.id}) has been processed."
                Notification.objects.create(user=purchase.created_by, message=msg, link="/inventory/purchases/")
            
            messages.success(request, "Purchase items processed and stock updated.")
            return redirect('purchase_list')
            
        return redirect('purchase_list')
    
    return render(request, 'inventory/purchase_approve.html', {'purchase': purchase})

from django.http import JsonResponse

@login_required
def design_search_ajax(request):
    q = request.GET.get('q', '')
    designs = DesignType.objects.all().select_related('collection')
    if q:
        designs = designs.filter(
            Q(name__icontains=q) |
            Q(alias1__icontains=q) |
            Q(alias2__icontains=q) |
            Q(alias3__icontains=q) |
            Q(alias4__icontains=q) |
            Q(alias5__icontains=q)
        )
    
    designs = designs[:30]
    
    results = []
    for d in designs:
        results.append({
            'id': d.id,
            'text': f"{d.collection.name if d.collection else 'No Collection'} - {d.name} (Alias: {d.alias1 or ''})",
            'price': float(d.default_price)
        })
    return JsonResponse({'results': results})
