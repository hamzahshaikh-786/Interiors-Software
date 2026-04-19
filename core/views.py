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
from payments.models import Payment

from django.core.management import call_command
from django.core.cache import cache

from django.contrib.auth import get_user_model
User = get_user_model()

from django.core.mail import send_mail
from django.conf import settings

def contact_us(request):
    if request.method == 'POST':
        first_name = request.POST.get('first_name', '')
        last_name = request.POST.get('last_name', '')
        email = request.POST.get('email', '')
        phone = request.POST.get('phone', '')
        message = request.POST.get('message', '')
        
        full_name = f"{first_name} {last_name}".strip()
        
        subject = f"New ERP Inquiry from {full_name}"
        email_message = f"Name: {full_name}\nEmail: {email}\nPhone: {phone}\n\nMessage:\n{message}"
        
        try:
            send_mail(
                subject,
                email_message,
                settings.DEFAULT_FROM_EMAIL,
                ['logicworks.official@gmail.com'],
                fail_silently=False,
            )
            messages.success(request, "Thank you! Your message has been sent. We'll get back to you soon.")
        except Exception as e:
            # Fallback for development if email is not configured
            messages.info(request, "Your message has been received! (Note: Email simulation in progress)")
            print(f"Email error: {e}")
            
        return redirect('contact_us')
        
    return render(request, 'core/contact.html')

@login_required
def dashboard(request):
    user = request.user
    context = {}

    # Automatic cleanup and notification check (once per day)
    if user.is_admin() or user.is_superadmin() or user.is_accountant():
        last_notif_date = cache.get('last_cheque_notif_date')
        today = timezone.localdate()
        
        if last_notif_date != today:
            try:
                # Run photo cleanup if needed
                last_cleanup = cache.get('last_photo_cleanup_date')
                if last_cleanup != today:
                    call_command('cleanup_photos')
                    cache.set('last_photo_cleanup_date', today, 86400)

                # Check for due cheques (including overdue ones)
                due_cheques = Payment.objects.filter(mode='cheque', is_deposited=False, cheque_date__lte=today)
                if due_cheques.exists():
                    count = due_cheques.count()
                    msg = f"Alert: {count} cheque{'s' if count > 1 else ''} are due for deposit!"
                    link = "/payments/cheques/"
                    
                    # Notify Admin and Accountants
                    notif_users = User.objects.filter(role__in=['admin', 'superadmin', 'accountant'])
                    for u in notif_users:
                        # Only create if not already notified today for the same count
                        Notification.objects.create(user=u, message=msg, link=link)
                
                cache.set('last_cheque_notif_date', today, 86400) # 24 hours
            except Exception as e:
                print(f"Error during automatic checks: {e}")

    if user.is_admin() or user.is_accountant():
        context['total_orders'] = Order.objects.count()
        context['pending_orders'] = Order.objects.filter(status='created').count()
        context['total_parties'] = Party.objects.count()
        context['low_stock_items'] = Stock.objects.filter(quantity__lte=models.F('low_stock_threshold'))
        
        # Monthly Sales
        now = timezone.localtime(timezone.now())
        month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
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

    elif user.is_cutter():
        return redirect('cutter_dashboard')

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
        selected_date = timezone.localdate()
        
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

def logout_view(request):
    if request.user.is_authenticated:
        logout(request)
        messages.success(request, "Logged out successfully")
    return redirect('login')
