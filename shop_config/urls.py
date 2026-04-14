from django.urls import path
from .views import shop_config_view

urlpatterns = [
    path('', shop_config_view, name='shop_config'),
]
