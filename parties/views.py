from django.shortcuts import render, redirect
from django.db import models
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.urls import reverse_lazy
from django.contrib import messages
from .models import Party
from decimal import Decimal
import pandas as pd

class AdminAccountantMixin(UserPassesTestMixin):
    def test_func(self):
        return self.request.user.is_admin() or self.request.user.is_accountant()

from django.utils import timezone
from datetime import timedelta

class MarketingAdminAccountantMixin(UserPassesTestMixin):
    def test_func(self):
        return self.request.user.is_admin() or self.request.user.is_accountant() or self.request.user.is_marketing_person()

class PartyListView(LoginRequiredMixin, MarketingAdminAccountantMixin, ListView):
    model = Party
    template_name = 'parties/party_list.html'
    context_object_name = 'parties'
    paginate_by = 20

    def get_queryset(self):
        queryset = super().get_queryset()
        query = self.request.GET.get('q')
        if query:
            queryset = queryset.filter(models.Q(name__icontains=query) | models.Q(phone__icontains=query) | models.Q(alias__icontains=query))
        
        # Inactive customer filters
        inactive_days = self.request.GET.get('inactive')
        if inactive_days in ['7', '15', '30']:
            days = int(inactive_days)
            threshold_date = timezone.now() - timedelta(days=days)
            # Find parties whose last order was before threshold_date
            from orders.models import Order
            active_party_ids = Order.objects.filter(created_at__gte=threshold_date).values_list('party_id', flat=True).distinct()
            queryset = queryset.exclude(id__in=active_party_ids)
            
        return queryset

    def get_template_names(self):
        if self.request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return ['parties/party_list_partial.html']
        return [self.template_name]

class PartyDetailView(LoginRequiredMixin, MarketingAdminAccountantMixin, DetailView):
    model = Party
    template_name = 'parties/party_detail.html'

class PartyCreateView(LoginRequiredMixin, AdminAccountantMixin, CreateView):
    model = Party
    fields = ['name', 'alias', 'phone', 'email', 'address', 'gst_number', 'credit_limit']
    template_name = 'parties/party_form.html'
    success_url = reverse_lazy('party_list')

class PartyUpdateView(LoginRequiredMixin, AdminAccountantMixin, UpdateView):
    model = Party
    fields = ['name', 'alias', 'phone', 'email', 'address', 'gst_number', 'credit_limit']
    template_name = 'parties/party_form.html'
    success_url = reverse_lazy('party_list')

class PartyDeleteView(LoginRequiredMixin, AdminAccountantMixin, DeleteView):
    model = Party
    template_name = 'parties/party_confirm_delete.html'
    success_url = reverse_lazy('party_list')

def party_import(request):
    if request.method == 'POST' and request.FILES.get('csv_file'):
        csv_file = request.FILES['csv_file']
        try:
            if csv_file.name.endswith('.csv'):
                df = pd.read_csv(csv_file)
            else:
                df = pd.read_excel(csv_file)
            
            # Normalize column names to lowercase and strip whitespace
            df.columns = [col.lower().strip() for col in df.columns]
            
            if 'name' not in df.columns:
                messages.error(request, "Error: 'name' column is missing from the file.")
                return redirect('party_import')
            
            count = 0
            for _, row in df.iterrows():
                party, created = Party.objects.get_or_create(
                    name=str(row['name']).strip(),
                    defaults={
                        'phone': str(row.get('phone', '')).strip(),
                        'email': str(row.get('email', '')).strip(),
                        'address': str(row.get('address', '')).strip(),
                        'gst_number': str(row.get('gst_number', '')).strip(),
                        'credit_limit': Decimal(str(row.get('credit_limit', '0')).strip() or '0')
                    }
                )
                if created:
                    count += 1
            messages.success(request, f"Successfully imported {count} new parties.")
        except Exception as e:
            messages.error(request, f"Error importing parties: {str(e)}")
        return redirect('party_list')
    return render(request, 'parties/party_import.html')
