from django.db import models
from parties.models import Party
from orders.models import Order
from payments.models import Payment

class Transaction(models.Model):
    TRANSACTION_TYPES = (
        ('sale', 'Sale'),
        ('payment', 'Payment'),
        ('return', 'Return'),
        ('adjustment', 'Adjustment'),
    )

    party = models.ForeignKey(Party, on_delete=models.CASCADE, related_name='ledger_entries')
    transaction_type = models.CharField(max_length=20, choices=TRANSACTION_TYPES)
    amount = models.DecimalField(max_digits=12, decimal_places=2) # Positive for debit, negative for credit or vice versa? 
    # Let's use standard: Debit (increase receivable), Credit (decrease receivable)
    # Sale = Debit, Payment = Credit
    debit = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    credit = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    
    order = models.ForeignKey(Order, on_delete=models.SET_NULL, null=True, blank=True)
    payment = models.ForeignKey(Payment, on_delete=models.SET_NULL, null=True, blank=True)
    
    description = models.TextField(blank=True, null=True)
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.party.name} - {self.transaction_type} - {self.amount}"

class PartyBalance(models.Model):
    party = models.OneToOneField(Party, on_delete=models.CASCADE, related_name='balance')
    total_debit = models.DecimalField(max_digits=15, decimal_places=2, default=0.00)
    total_credit = models.DecimalField(max_digits=15, decimal_places=2, default=0.00)
    current_balance = models.DecimalField(max_digits=15, decimal_places=2, default=0.00) # debit - credit
    last_updated = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.party.name} Balance: {self.current_balance}"
