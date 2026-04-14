from django.urls import path
from . import views

urlpatterns = [
    path('add/<int:order_id>/', views.PaymentCreateView.as_view(), name='payment_add'),
]
