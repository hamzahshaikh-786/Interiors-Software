from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from .models import ShopConfiguration

def is_admin(user):
    return user.is_authenticated and hasattr(user, 'role') and user.role == 'admin'

@login_required
@user_passes_test(is_admin)
def shop_config_view(request):
    config = ShopConfiguration.objects.first()
    if request.method == 'POST':
        shop_name = request.POST.get('shop_name')
        upi_id = request.POST.get('upi_id')
        
        if not config:
            config = ShopConfiguration.objects.create(shop_name=shop_name, upi_id=upi_id)
        else:
            config.shop_name = shop_name
            config.upi_id = upi_id
            config.save()
            
        messages.success(request, "Shop configuration updated successfully.")
        return redirect('shop_config')

    upi_preview_url = config.build_upi_url() if config else None
    return render(request, 'shop_config/config_form.html', {'config': config, 'upi_preview_url': upi_preview_url})
