from django.db import models
from orders.models import Order
from django.conf import settings

class Payment(models.Model):
    PAYMENT_MODES = (
        ('upi', 'UPI'),
        ('cash', 'Cash'),
        ('bank_transfer', 'Bank Transfer'),
    )

    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='payments')
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    mode = models.CharField(max_length=20, choices=PAYMENT_MODES)
    transaction_id = models.CharField(max_length=100, blank=True, null=True)
    recorded_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    timestamp = models.DateTimeField(auto_now_add=True)
    notes = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"Payment of {self.amount} for {self.order.invoice_number}"
