from django.db import models
from django.conf import settings
from parties.models import Party
from inventory.models import DesignType
import uuid

class Order(models.Model):
    STATUS_CHOICES = (
        ('created', 'Created'),
        ('cutting', 'Cutting'),
        ('ready', 'Ready'),
        ('assigned', 'Assigned'),
        ('out_for_delivery', 'Out for Delivery'),
        ('delivered', 'Delivered'),
        ('paid', 'Paid'),
        ('cancelled', 'Cancelled'),
    )

    invoice_number = models.CharField(max_length=50, unique=True, blank=True)
    party = models.ForeignKey(Party, on_delete=models.CASCADE, related_name='orders')
    delivery_address = models.TextField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='created')
    
    # Delivery Info
    DELIVERY_METHOD_CHOICES = (
        ('self', 'Self'),
        ('porter', 'Porter'),
        ('courier', 'Courier'),
        ('delivery_man', 'Delivery Man'),
    )
    delivery_method = models.CharField(max_length=20, choices=DELIVERY_METHOD_CHOICES, default='self')
    delivery_reference_number = models.CharField(max_length=100, blank=True, null=True)
    
    # Financials
    total_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    gst_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    grand_total = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    balance_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)

    # Assignments
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='created_orders')
    warehouse_manager = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='managed_orders')
    delivery_partner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='delivered_orders')

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        if not self.invoice_number:
            self.invoice_number = f"INV-{uuid.uuid4().hex[:8].upper()}"
        super().save(*args, **kwargs)

    def __str__(self):
        return self.invoice_number

    def can_transition_to(self, next_status):
        # Define valid transitions
        valid_transitions = {
            'created': ['cutting', 'cancelled'],
            'cutting': ['ready', 'cancelled'],
            'ready': ['assigned', 'cancelled'],
            'assigned': ['out_for_delivery', 'cancelled'],
            'out_for_delivery': ['delivered', 'cancelled'],
            'delivered': ['paid'],
            'paid': [],
            'cancelled': [],
        }
        return next_status in valid_transitions.get(self.status, [])

    def transition_to(self, next_status, user, notes=None):
        if self.can_transition_to(next_status):
            old_status = self.status
            self.status = next_status
            self.save()
            
            # Log history
            OrderStatusHistory.objects.create(
                order=self,
                status=next_status,
                updated_by=user,
                notes=notes
            )
            
            # Business logic for specific transitions
            if old_status == 'cutting' and next_status == 'ready':
                # Decrease inventory
                from inventory.models import Stock
                for item in self.items.all():
                    stock, created = Stock.objects.get_or_create(design_type=item.design_type)
                    stock.quantity -= item.quantity
                    stock.save()
            
            return True
        return False

class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
    design_type = models.ForeignKey(DesignType, on_delete=models.CASCADE, null=True)
    quantity = models.DecimalField(max_digits=10, decimal_places=2) # in meters
    price_per_meter = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    total_price = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)

    def save(self, *args, **kwargs):
        if self.price_per_meter:
            self.total_price = self.quantity * self.price_per_meter
        else:
            self.total_price = 0
        super().save(*args, **kwargs)

class OrderStatusHistory(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='status_history')
    status = models.CharField(max_length=20, choices=Order.STATUS_CHOICES)
    updated_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    timestamp = models.DateTimeField(auto_now_add=True)
    notes = models.TextField(blank=True, null=True)

    class Meta:
        verbose_name_plural = "Order status histories"
