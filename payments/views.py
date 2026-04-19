from django.shortcuts import render, get_object_or_404, redirect
from django.views.generic import CreateView, ListView
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from .models import Payment
from orders.models import Order
from ledger.models import Transaction, PartyBalance
from django.db import transaction
from django.contrib import messages
from django.contrib.auth.decorators import login_required

class AdminAccountantMixin(UserPassesTestMixin):
    def test_func(self):
        return self.request.user.is_admin() or self.request.user.is_accountant()

class PaymentCreateView(LoginRequiredMixin, CreateView):
    model = Payment
    fields = ['amount', 'mode', 'transaction_id', 'cheque_date', 'notes']
    template_name = 'payments/payment_form.html'

    def form_valid(self, form):
        order = get_object_or_404(Order, id=self.kwargs['order_id'])
        with transaction.atomic():
            payment = form.save(commit=False)
            payment.order = order
            payment.recorded_by = self.request.user
            payment.save()

            order.balance_amount -= payment.amount
            if order.balance_amount <= 0:
                order.status = 'paid'
            order.save()

            # Ledger entry
            Transaction.objects.create(
                party=order.party,
                transaction_type='payment',
                amount=payment.amount,
                credit=payment.amount,
                order=order,
                payment=payment,
                description=f"Payment for {order.invoice_number} ({payment.get_mode_display()})"
            )

            # Update Balance
            balance = order.party.balance
            balance.total_credit += payment.amount
            balance.current_balance -= payment.amount
            balance.save()

        messages.success(self.request, "Payment recorded successfully.")
        return redirect('order_detail', pk=order.pk)

class ChequeRegisterView(LoginRequiredMixin, AdminAccountantMixin, ListView):
    model = Payment
    template_name = 'payments/cheque_register.html'
    context_object_name = 'cheques'

    def get_queryset(self):
        return Payment.objects.filter(mode='cheque').order_by('is_deposited', 'cheque_date')

@login_required
def mark_cheque_deposited(request, pk):
    if not (request.user.is_admin() or request.user.is_accountant()):
        return redirect('dashboard')
    
    cheque = get_object_or_404(Payment, pk=pk, mode='cheque')
    cheque.is_deposited = True
    cheque.save()
    messages.success(request, f"Cheque for {cheque.order.party.name} marked as deposited.")
    return redirect('cheque_register')
