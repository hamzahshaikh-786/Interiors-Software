from django.shortcuts import render, get_object_or_404, redirect
from django.views.generic import CreateView
from django.contrib.auth.mixins import LoginRequiredMixin
from .models import Payment
from orders.models import Order
from ledger.models import Transaction, PartyBalance
from django.db import transaction

class PaymentCreateView(LoginRequiredMixin, CreateView):
    model = Payment
    fields = ['amount', 'mode', 'transaction_id', 'notes']
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
                description=f"Payment for {order.invoice_number}"
            )

            # Update Balance
            balance = order.party.balance
            balance.total_credit += payment.amount
            balance.current_balance -= payment.amount
            balance.save()

        return redirect('order_detail', pk=order.pk)
