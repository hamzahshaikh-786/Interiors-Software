from django.db import models
from django.contrib.auth.models import AbstractUser

class User(AbstractUser):
    SUPERADMIN = 'superadmin'
    ADMIN = 'admin'
    ACCOUNTANT = 'accountant'
    WAREHOUSE_MANAGER = 'warehouse_manager'
    DELIVERY_PERSON = 'delivery_person'
    MARKETING_PERSON = 'marketing_person'

    ROLE_CHOICES = (
        (SUPERADMIN, 'SuperAdmin'),
        (ADMIN, 'Admin'),
        (ACCOUNTANT, 'Accountant'),
        (WAREHOUSE_MANAGER, 'Warehouse Manager'),
        (DELIVERY_PERSON, 'Delivery Person'),
        (MARKETING_PERSON, 'Marketing Person'),
    )

    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default=ADMIN)
    phone_number = models.CharField(max_length=15, blank=True, null=True)

    def is_superadmin(self):
        return self.role == self.SUPERADMIN

    def is_admin(self):
        return self.role == self.ADMIN or self.role == self.SUPERADMIN

    def is_accountant(self):
        return self.role == self.ACCOUNTANT

    def is_warehouse_manager(self):
        return self.role == self.WAREHOUSE_MANAGER

    def is_delivery_person(self):
        return self.role == self.DELIVERY_PERSON

    def is_marketing_person(self):
        return self.role == self.MARKETING_PERSON
