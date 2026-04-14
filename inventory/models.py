from django.db import models

class Collection(models.Model):
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

class DesignType(models.Model):
    collection = models.ForeignKey(Collection, on_delete=models.CASCADE, related_name='designs', null=True, blank=True)
    name = models.CharField(max_length=100)
    alias1 = models.CharField(max_length=100, blank=True, null=True)
    alias2 = models.CharField(max_length=100, blank=True, null=True)
    alias3 = models.CharField(max_length=100, blank=True, null=True)
    alias4 = models.CharField(max_length=100, blank=True, null=True)
    alias5 = models.CharField(max_length=100, blank=True, null=True)
    description = models.TextField(blank=True, null=True)
    unit = models.CharField(max_length=20, default='meters')
    default_price = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.collection.name} - {self.name}" if self.collection else self.name

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['collection', 'name'], name='uniq_design_name_per_collection'),
        ]

class Stock(models.Model):
    design_type = models.OneToOneField(DesignType, on_delete=models.CASCADE, related_name='stock', null=True)
    quantity = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    low_stock_threshold = models.DecimalField(max_digits=12, decimal_places=2, default=10.00)
    last_updated = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.design_type.name} - {self.quantity} {self.design_type.unit}"

    def is_low_stock(self):
        return self.quantity <= self.low_stock_threshold

class Purchaser(models.Model):
    name = models.CharField(max_length=100, unique=True)
    phone = models.CharField(max_length=15, blank=True, null=True)
    address = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

class PurchaseEntry(models.Model):
    STATUS_CHOICES = (
        ('pending', 'Pending Approval'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    )

    reference_bill_number = models.CharField(max_length=100, blank=True, null=True)
    purchaser = models.ForeignKey(Purchaser, on_delete=models.CASCADE, related_name='purchases')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    created_by = models.ForeignKey('users.User', on_delete=models.CASCADE, related_name='created_purchases')
    approved_by = models.ForeignKey('users.User', on_delete=models.SET_NULL, null=True, blank=True, related_name='approved_purchases')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Purchase {self.reference_bill_number} - {self.purchaser.name}"

class PurchaseItem(models.Model):
    CONDITION_CHOICES = (
        ('good', 'Good'),
        ('bad', 'Bad'),
    )
    COLOUR_MATCH_CHOICES = (
        ('match', 'Match'),
        ('unmatch', 'Unmatch'),
    )
    ITEM_STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    )

    purchase_entry = models.ForeignKey(PurchaseEntry, on_delete=models.CASCADE, related_name='items')
    design_type = models.ForeignKey(DesignType, on_delete=models.CASCADE)
    quantity = models.DecimalField(max_digits=12, decimal_places=2)
    material_condition = models.CharField(max_length=10, choices=CONDITION_CHOICES)
    design_colour_match = models.CharField(max_length=10, choices=COLOUR_MATCH_CHOICES)
    status = models.CharField(max_length=20, choices=ITEM_STATUS_CHOICES, default='pending')

    def __str__(self):
        return f"{self.design_type.name} - {self.quantity}"
