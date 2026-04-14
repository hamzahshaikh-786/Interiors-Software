from django.shortcuts import render, get_object_or_404
from django.views.generic import ListView
from decimal import Decimal
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from .models import PartyBalance, Transaction
from parties.models import Party

class AdminAccountantMixin(UserPassesTestMixin):
    def test_func(self):
        return self.request.user.is_admin() or self.request.user.is_accountant()

class LedgerListView(LoginRequiredMixin, AdminAccountantMixin, ListView):
    model = PartyBalance
    template_name = 'ledger/ledger_list.html'
    context_object_name = 'balances'

def party_ledger(request, party_id):
    party = get_object_or_404(Party, id=party_id)
    transactions = Transaction.objects.filter(party=party).select_related('order', 'payment').order_by('timestamp')
    balance_obj = PartyBalance.objects.get_or_create(party=party)[0]
    
    # Calculate running balance
    running_balance = Decimal('0.00')
    ledger_entries = []
    for t in transactions:
        running_balance += (t.debit - t.credit)
        ledger_entries.append({
            'transaction': t,
            'running_balance': running_balance
        })
    
    # Reverse for display (newest first)
    ledger_entries.reverse()
    
    return render(request, 'ledger/party_ledger.html', {
        'party': party,
        'ledger_entries': ledger_entries,
        'balance': balance_obj
    })
