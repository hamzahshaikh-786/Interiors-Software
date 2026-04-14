from django.urls import path
from . import views

urlpatterns = [
    path('', views.PartyListView.as_view(), name='party_list'),
    path('add/', views.PartyCreateView.as_view(), name='party_add'),
    path('<int:pk>/', views.PartyDetailView.as_view(), name='party_detail'),
    path('<int:pk>/edit/', views.PartyUpdateView.as_view(), name='party_edit'),
    path('<int:pk>/delete/', views.PartyDeleteView.as_view(), name='party_delete'),
    path('import/', views.party_import, name='party_import'),
]
