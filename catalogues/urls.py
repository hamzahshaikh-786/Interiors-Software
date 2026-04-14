from django.urls import path
from . import views

urlpatterns = [
    # Catalogue Types
    path('types/', views.CatalogueTypeListView.as_view(), name='catalogue_type_list'),
    path('types/add/', views.CatalogueTypeCreateView.as_view(), name='catalogue_type_add'),
    path('types/<int:pk>/edit/', views.CatalogueTypeUpdateView.as_view(), name='catalogue_type_edit'),
    path('types/<int:pk>/delete/', views.CatalogueTypeDeleteView.as_view(), name='catalogue_type_delete'),

    # Inventory
    path('inventory/', views.catalogue_inventory_list, name='catalogue_inventory_list'),

    # Purchases
    path('purchases/', views.catalogue_purchase_list, name='catalogue_purchase_list'),
    path('purchases/add/', views.catalogue_purchase_create, name='catalogue_purchase_add'),

    # Distributions
    path('distributions/', views.catalogue_distribution_list, name='catalogue_distribution_list'),
    path('distributions/add/', views.catalogue_distribution_create, name='catalogue_distribution_add'),

    # Visits
    path('visits/', views.catalogue_visit_list, name='catalogue_visit_list'),
    path('visits/add/', views.catalogue_visit_create, name='catalogue_visit_add'),
    path('ajax/assigned-catalogues/<int:party_id>/', views.get_assigned_catalogues, name='ajax_assigned_catalogues'),
]
