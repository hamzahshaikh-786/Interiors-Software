from .models import ShopConfiguration

def shop_info(request):
    config, created = ShopConfiguration.objects.get_or_create(pk=1, defaults={'shop_name': 'Interior Soft'})
    return {
        'shop_config': config
    }
