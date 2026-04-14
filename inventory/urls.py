from django.urls import path
from . import views

urlpatterns = [
    path('stock/', views.StockListView.as_view(), name='stock_list'),
    path('stock/<int:pk>/update/', views.StockUpdateView.as_view(), name='stock_update'),
    
    # Collection URLs
    path('collections/', views.CollectionListView.as_view(), name='collection_list'),
    path('collections/add/', views.CollectionCreateView.as_view(), name='collection_create'),
    path('collections/<int:pk>/edit/', views.CollectionUpdateView.as_view(), name='collection_update'),
    path('collections/<int:pk>/delete/', views.CollectionDeleteView.as_view(), name='collection_delete'),
    
    # DesignType URLs
    path('designs/add/', views.DesignTypeCreateView.as_view(), name='designtype_create'),
    path('designs/<int:pk>/edit/', views.DesignTypeUpdateView.as_view(), name='designtype_update'),
    path('designs/<int:pk>/delete/', views.DesignTypeDeleteView.as_view(), name='designtype_delete'),
    
    # Purchaser URLs
    path('purchasers/', views.PurchaserListView.as_view(), name='purchaser_list'),
    path('purchasers/add/', views.PurchaserCreateView.as_view(), name='purchaser_create'),
    path('purchasers/<int:pk>/edit/', views.PurchaserUpdateView.as_view(), name='purchaser_update'),
    path('purchasers/<int:pk>/delete/', views.PurchaserDeleteView.as_view(), name='purchaser_delete'),
    
    # Purchase Entry URLs
    path('purchases/', views.purchase_list, name='purchase_list'),
    path('purchases/add/', views.purchase_entry_create, name='purchase_create'),
    path('purchases/<int:pk>/approve/', views.purchase_approve, name='purchase_approve'),
    path('designs/search/', views.design_search_ajax, name='design_search_ajax'),
]
