from django.urls import path
from . import views

urlpatterns = [
    path('', views.LedgerListView.as_view(), name='ledger_list'),
    path('<int:party_id>/', views.party_ledger, name='party_ledger'),
]
