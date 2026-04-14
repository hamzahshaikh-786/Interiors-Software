"""
URL configuration for interior_soft project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/4.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from django.contrib.auth import views as auth_views
from core import views as core_views
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', core_views.dashboard, name='dashboard'),
    path('analytics/', core_views.analytics_dashboard, name='analytics'),
    path('daybook/', core_views.daybook, name='daybook'),
    path('notifications/<int:pk>/seen/', core_views.mark_notification_seen, name='notification_seen'),
    path('login/', auth_views.LoginView.as_view(template_name='registration/login.html', redirect_authenticated_user=True), name='login'),
    path('logout/', core_views.logout_view, name='logout'),
    
    path('parties/', include('parties.urls')),
    path('orders/', include('orders.urls')),
    path('inventory/', include('inventory.urls')),
    path('ledger/', include('ledger.urls')),
    path('payments/', include('payments.urls')),
    path('shop-config/', include('shop_config.urls')),
    path('users/', include('users.urls')),
    path('catalogues/', include('catalogues.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
