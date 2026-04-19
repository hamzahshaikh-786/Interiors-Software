from django.urls import path
from . import views

urlpatterns = [
    path('', views.OrderListView.as_view(), name='order_list'),
    path('create/', views.order_create, name='order_create'),
    path('<int:pk>/', views.OrderDetailView.as_view(), name='order_detail'),
    path('<int:pk>/status/<str:status>/', views.order_status_update, name='order_status_update'),
    
    # Dashboards
    path('warehouse/', views.warehouse_dashboard, name='warehouse_dashboard'),
    path('cutter/', views.cutter_dashboard, name='cutter_dashboard'),
    path('delivery/', views.delivery_dashboard, name='delivery_dashboard'),
    
    # Delivery Actions
    path('<int:pk>/pickup/', views.order_pickup, name='order_pickup'),
    path('<int:pk>/deliver/', views.order_mark_delivered, name='order_mark_delivered'),
    path('<int:pk>/challan/', views.delivery_challan_pdf, name='delivery_challan'),
    path('<int:pk>/invoice/', views.generate_invoice_pdf, name='order_invoice'),
]
