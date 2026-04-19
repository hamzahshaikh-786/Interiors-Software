from django.urls import path
from . import views

urlpatterns = [
    path('add/<int:order_id>/', views.PaymentCreateView.as_view(), name='payment_add'),
    path('cheques/', views.ChequeRegisterView.as_view(), name='cheque_register'),
    path('cheques/<int:pk>/deposit/', views.mark_cheque_deposited, name='mark_cheque_deposited'),
]
