from django.contrib import admin
from .models import ShopConfiguration

@admin.register(ShopConfiguration)
class ShopConfigurationAdmin(admin.ModelAdmin):
    def has_add_permission(self, request):
        # Only allow one config
        return not ShopConfiguration.objects.exists()
    
    def has_delete_permission(self, request, obj=None):
        return False
