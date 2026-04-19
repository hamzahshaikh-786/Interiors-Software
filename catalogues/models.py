from django.db import models
from django.conf import settings
from parties.models import Party, Vendor

class CatalogueType(models.Model):
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

class CatalogueInventory(models.Model):
    catalogue_type = models.OneToOneField(CatalogueType, on_delete=models.CASCADE, related_name='inventory')
    quantity = models.PositiveIntegerField(default=0)
    last_updated = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.catalogue_type.name}: {self.quantity}"

class CataloguePurchase(models.Model):
    vendor = models.ForeignKey(Vendor, on_delete=models.CASCADE, related_name='catalogue_purchases', null=True, blank=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    notes = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"Catalogue Purchase {self.id} from {self.vendor.name}"

class CataloguePurchaseItem(models.Model):
    purchase = models.ForeignKey(CataloguePurchase, on_delete=models.CASCADE, related_name='items')
    catalogue_type = models.ForeignKey(CatalogueType, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField()

    def __str__(self):
        return f"{self.catalogue_type.name} - {self.quantity}"

class CatalogueDistribution(models.Model):
    party = models.ForeignKey(Party, on_delete=models.CASCADE, related_name='catalogue_distributions')
    distributed_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    distributed_at = models.DateTimeField(auto_now_add=True)
    notes = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"Distribution to {self.party.name} on {self.distributed_at}"

class CatalogueDistributionItem(models.Model):
    distribution = models.ForeignKey(CatalogueDistribution, on_delete=models.CASCADE, related_name='items')
    catalogue_type = models.ForeignKey(CatalogueType, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField()

    def __str__(self):
        return f"{self.catalogue_type.name} - {self.quantity}"

class CatalogueVisit(models.Model):
    party = models.ForeignKey(Party, on_delete=models.CASCADE, related_name='catalogue_visits')
    visited_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    visit_date = models.DateField()
    photo = models.ImageField(upload_to='catalogue_visits/', blank=True, null=True)
    notes = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    # Store checked and missing catalogues as JSON or separate model. 
    # For simplicity and clear tracking, let's use a through model for checked items.
    
    def __str__(self):
        return f"Visit to {self.party.name} by {self.visited_by.username} on {self.visit_date}"

class CatalogueVisitItem(models.Model):
    visit = models.ForeignKey(CatalogueVisit, on_delete=models.CASCADE, related_name='items')
    catalogue_type = models.ForeignKey(CatalogueType, on_delete=models.CASCADE)
    is_present = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.catalogue_type.name} present: {self.is_present}"
