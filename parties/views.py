from django.shortcuts import render, redirect
from django.db import models
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.urls import reverse_lazy
from django.contrib import messages
from .models import Party, Vendor
from decimal import Decimal
# import pandas as pd

class AdminAccountantMixin(UserPassesTestMixin):
    def test_func(self):
        return self.request.user.is_admin() or self.request.user.is_accountant()

class CatalogueManagementMixin(UserPassesTestMixin):
    def test_func(self):
        return self.request.user.is_authenticated and (
            self.request.user.is_admin() or 
            self.request.user.is_accountant() or 
            self.request.user.is_marketing_person()
        )

class VendorListView(LoginRequiredMixin, CatalogueManagementMixin, ListView):
    model = Vendor
    template_name = 'parties/party_list.html' # Reuse party list template for simplicity
    context_object_name = 'vendors'
    paginate_by = 20

    def get_queryset(self):
        queryset = super().get_queryset()
        query = self.request.GET.get('q')
        if query:
            queryset = queryset.filter(models.Q(name__icontains=query) | models.Q(phone__icontains=query) | models.Q(alias__icontains=query))
        return queryset

    def get_template_names(self):
        if self.request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return ['parties/party_list_partial.html']
        return [self.template_name]

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['is_vendor_list'] = True
        return context

class VendorCreateView(LoginRequiredMixin, CatalogueManagementMixin, CreateView):
    model = Vendor
    fields = ['name', 'alias', 'phone', 'email', 'address']
    template_name = 'parties/party_form.html' # Reuse party form
    success_url = reverse_lazy('vendor_list')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['is_vendor_form'] = True
        return context

class VendorUpdateView(LoginRequiredMixin, CatalogueManagementMixin, UpdateView):
    model = Vendor
    fields = ['name', 'alias', 'phone', 'email', 'address']
    template_name = 'parties/party_form.html'
    success_url = reverse_lazy('vendor_list')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['is_vendor_form'] = True
        return context

class VendorDeleteView(LoginRequiredMixin, CatalogueManagementMixin, DeleteView):
    model = Vendor
    template_name = 'parties/party_confirm_delete.html'
    success_url = reverse_lazy('vendor_list')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['is_vendor_delete'] = True
        return context

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

import pandas as pd

def party_import(request):
    if request.method == 'POST' and request.FILES.get('csv_file'):
        csv_file = request.FILES['csv_file']
        try:
            if csv_file.name.endswith('.csv'):
                df = pd.read_csv(csv_file)
            else:
                df = pd.read_excel(csv_file)
            
            # Normalize column names for checking
            original_columns = [str(col).lower().strip() for col in df.columns]
            
            # Define common headers we expect
            common_headers = {'name', 'party name', 'party', 'customer name', 'customer', 'phone', 'email', 'address', 'gst', 'gst_number', 'limit', 'credit_limit'}
            
            # Count how many original columns match our known headers
            matches = sum(1 for col in original_columns if col in common_headers)
            
            # If less than 2 columns match, or 'name' variation is not found, 
            # it's very likely the first row is actually data.
            has_name_header = any(h in original_columns for h in ['name', 'party name', 'party', 'customer name', 'customer'])
            
            if matches < 2 or not has_name_header:
                # Re-read without header to treat the first row as data
                if csv_file.name.endswith('.csv'):
                    csv_file.seek(0)
                    df = pd.read_csv(csv_file, header=None)
                else:
                    df = pd.read_excel(csv_file, header=None)
                
                # Default mapping based on user's hint: Name, Phone, Email, Address, GST, Limit
                cols = ['name', 'phone', 'email', 'address', 'gst_number', 'credit_limit']
                df.columns = cols[:len(df.columns)]
            else:
                df.columns = original_columns

            # Re-identify name column after potential re-read
            name_col = None
            for col in df.columns:
                if col in ['name', 'party name', 'party', 'customer name', 'customer', 0]:
                    name_col = col
                    break
            
            if name_col is None:
                messages.error(request, f"Error: 'name' column is missing. Found: {', '.join(map(str, df.columns))}")
                return redirect('party_import')
            
            count = 0
            for _, row in df.iterrows():
                name_val = str(row.get(name_col, '')).strip()
                # Skip truly empty rows or 'nan'
                if not name_val or name_val.lower() in ['nan', 'none', '']:
                    continue

                # Mapping logic for data rows
                phone = str(row.get('phone', row.get(1, ''))).strip()
                email = str(row.get('email', row.get(2, ''))).strip()
                address = str(row.get('address', row.get(3, ''))).strip()
                gst = str(row.get('gst_number', row.get(4, ''))).strip()
                try:
                    limit_raw = str(row.get('credit_limit', row.get(5, '0'))).strip()
                    limit = Decimal(limit_raw or '0')
                except:
                    limit = Decimal('0')

                party, created = Party.objects.get_or_create(
                    name=name_val,
                    defaults={
                        'phone': phone,
                        'email': email,
                        'address': address,
                        'gst_number': gst,
                        'credit_limit': limit
                    }
                )
                if created:
                    count += 1
            messages.success(request, f"Successfully imported {count} new parties.")
        except Exception as e:
            messages.error(request, f"Error importing parties: {str(e)}")
        return redirect('party_list')
    return render(request, 'parties/party_import.html')
