from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.db import transaction
from django.db.models import Q, Sum, Count
from django.urls import reverse_lazy
from django.views.generic import ListView, CreateView, UpdateView, DeleteView
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from .models import (
    CatalogueType, CatalogueInventory, CataloguePurchase, 
    CataloguePurchaseItem, CatalogueDistribution, CatalogueDistributionItem, 
    CatalogueVisit, CatalogueVisitItem
)
from parties.models import Party
from django.http import JsonResponse

def can_manage_catalogues(user):
    return user.is_authenticated and (user.is_admin() or user.is_accountant() or user.is_marketing_person())

class CatalogueAccessMixin(UserPassesTestMixin):
    def test_func(self):
        return can_manage_catalogues(self.request.user)

# Catalogue Type CRUD
class CatalogueTypeListView(LoginRequiredMixin, CatalogueAccessMixin, ListView):
    model = CatalogueType
    template_name = 'catalogues/type_list.html'
    context_object_name = 'types'

class CatalogueTypeCreateView(LoginRequiredMixin, CatalogueAccessMixin, CreateView):
    model = CatalogueType
    fields = ['name', 'description']
    template_name = 'catalogues/type_form.html'
    success_url = reverse_lazy('catalogue_type_list')

    def form_valid(self, form):
        response = super().form_valid(form)
        CatalogueInventory.objects.get_or_create(catalogue_type=self.object)
        messages.success(self.request, f"Catalogue type {self.object.name} created.")
        return response

class CatalogueTypeUpdateView(LoginRequiredMixin, CatalogueAccessMixin, UpdateView):
    model = CatalogueType
    fields = ['name', 'description']
    template_name = 'catalogues/type_form.html'
    success_url = reverse_lazy('catalogue_type_list')

class CatalogueTypeDeleteView(LoginRequiredMixin, CatalogueAccessMixin, DeleteView):
    model = CatalogueType
    template_name = 'catalogues/type_confirm_delete.html'
    success_url = reverse_lazy('catalogue_type_list')

# Catalogue Stock Purchase
@login_required
@user_passes_test(can_manage_catalogues)
def catalogue_purchase_create(request):
    if request.method == 'POST':
        party_id = request.POST.get('party')
        type_ids = request.POST.getlist('catalogue_type')
        quantities = request.POST.getlist('quantity')
        notes = request.POST.get('notes')

        party = get_object_or_404(Party, id=party_id)
        
        with transaction.atomic():
            purchase = CataloguePurchase.objects.create(
                party=party,
                created_by=request.user,
                notes=notes
            )
            for t_id, qty in zip(type_ids, quantities):
                if not t_id or not qty: continue
                c_type = get_object_or_404(CatalogueType, id=t_id)
                CataloguePurchaseItem.objects.create(
                    purchase=purchase,
                    catalogue_type=c_type,
                    quantity=qty
                )
                # Update inventory
                inv, _ = CatalogueInventory.objects.get_or_create(catalogue_type=c_type)
                inv.quantity += int(qty)
                inv.save()
        
        messages.success(request, "Catalogue stock purchase recorded.")
        return redirect('catalogue_purchase_list')

    parties = Party.objects.all()
    catalogue_types = CatalogueType.objects.all()
    return render(request, 'catalogues/purchase_form.html', {
        'parties': parties,
        'catalogue_types': catalogue_types
    })

@login_required
@user_passes_test(can_manage_catalogues)
def catalogue_purchase_list(request):
    purchases = CataloguePurchase.objects.all().order_by('-created_at').select_related('party', 'created_by').prefetch_related('items__catalogue_type')
    return render(request, 'catalogues/purchase_list.html', {'purchases': purchases})

# Catalogue Distribution
@login_required
@user_passes_test(can_manage_catalogues)
def catalogue_distribution_create(request):
    if request.method == 'POST':
        party_id = request.POST.get('party')
        type_ids = request.POST.getlist('catalogue_type')
        quantities = request.POST.getlist('quantity')
        notes = request.POST.get('notes')

        party = get_object_or_404(Party, id=party_id)
        
        with transaction.atomic():
            # First check stock
            items_to_create = []
            for t_id, qty in zip(type_ids, quantities):
                if not t_id or not qty: continue
                c_type = get_object_or_404(CatalogueType, id=t_id)
                qty_int = int(qty)
                inv = CatalogueInventory.objects.get(catalogue_type=c_type)
                if inv.quantity < qty_int:
                    messages.error(request, f"Insufficient stock for {c_type.name}. Available: {inv.quantity}")
                    return redirect('catalogue_distribution_create')
                items_to_create.append((c_type, qty_int))

            distribution = CatalogueDistribution.objects.create(
                party=party,
                distributed_by=request.user,
                notes=notes
            )
            for c_type, qty_int in items_to_create:
                CatalogueDistributionItem.objects.create(
                    distribution=distribution,
                    catalogue_type=c_type,
                    quantity=qty_int
                )
                # Update inventory
                inv = CatalogueInventory.objects.get(catalogue_type=c_type)
                inv.quantity -= qty_int
                inv.save()
        
        messages.success(request, f"Catalogues distributed to {party.name}.")
        return redirect('catalogue_distribution_list')

    parties = Party.objects.all()
    catalogue_types = CatalogueType.objects.filter(inventory__quantity__gt=0)
    return render(request, 'catalogues/distribution_form.html', {
        'parties': parties,
        'catalogue_types': catalogue_types
    })

@login_required
@user_passes_test(can_manage_catalogues)
def catalogue_distribution_list(request):
    distributions = CatalogueDistribution.objects.all().order_by('-distributed_at').select_related('party', 'distributed_by').prefetch_related('items__catalogue_type')
    return render(request, 'catalogues/distribution_list.html', {'distributions': distributions})

# Catalogue Visit
@login_required
@user_passes_test(can_manage_catalogues)
def catalogue_visit_create(request):
    if request.method == 'POST':
        party_id = request.POST.get('party')
        visit_date = request.POST.get('visit_date')
        photo_data = request.POST.get('photo_data')
        notes = request.POST.get('notes')
        present_type_ids = request.POST.getlist('present_catalogues')

        party = get_object_or_404(Party, id=party_id)
        
        # Get all assigned catalogues for this party
        assigned = CatalogueDistributionItem.objects.filter(
            distribution__party=party
        ).values('catalogue_type').annotate(total=Sum('quantity'))

        with transaction.atomic():
            visit = CatalogueVisit.objects.create(
                party=party,
                visited_by=request.user,
                visit_date=visit_date,
                notes=notes
            )
            
            # Handle photo optimization
            if photo_data:
                import uuid
                from django.core.files.base import ContentFile
                import base64
                
                format, imgstr = photo_data.split(';base64,') 
                ext = format.split('/')[-1] 
                file_name = f"visit_{uuid.uuid4()}.{ext}"
                visit.photo.save(file_name, ContentFile(base64.b64decode(imgstr)), save=False)

            visit.save()

            for item in assigned:
                t_id = item['catalogue_type']
                c_type = CatalogueType.objects.get(id=t_id)
                is_present = str(t_id) in present_type_ids
                CatalogueVisitItem.objects.create(
                    visit=visit,
                    catalogue_type=c_type,
                    is_present=is_present
                )
        
        messages.success(request, f"Visit to {party.name} recorded.")
        return redirect('catalogue_visit_list')

    parties = Party.objects.annotate(dist_count=Count('catalogue_distributions')).filter(dist_count__gt=0)
    return render(request, 'catalogues/visit_form.html', {'parties': parties})

@login_required
def get_assigned_catalogues(request, party_id):
    party = get_object_or_404(Party, id=party_id)
    assigned = CatalogueDistributionItem.objects.filter(
        distribution__party=party
    ).values('catalogue_type', 'catalogue_type__name').annotate(total=Sum('quantity'))
    
    return JsonResponse({'catalogues': list(assigned)})

@login_required
@user_passes_test(can_manage_catalogues)
def catalogue_visit_list(request):
    mode = request.GET.get('mode', 'chronological')
    visits = CatalogueVisit.objects.all().select_related('party', 'visited_by').prefetch_related('items__catalogue_type')
    
    if mode == 'shop':
        # Grouping logic will be handled in template or by ordering
        visits = visits.order_by('party__name', '-visit_date')
    else:
        visits = visits.order_by('-visit_date')

    # Add summary to each visit
    for visit in visits:
        total = visit.items.count()
        present = visit.items.filter(is_present=True).count()
        visit.summary = f"All {total} present" if total == present else f"{total - present} missing"
        visit.all_present = (total == present)

    return render(request, 'catalogues/visit_list.html', {
        'visits': visits,
        'mode': mode
    })

@login_required
@user_passes_test(can_manage_catalogues)
def catalogue_inventory_list(request):
    inventory = CatalogueInventory.objects.all().select_related('catalogue_type').order_by('catalogue_type__name')
    return render(request, 'catalogues/inventory_list.html', {'inventory': inventory})
