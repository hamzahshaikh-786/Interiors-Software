from django.urls import path
from . import views

urlpatterns = [
    path('list/', views.user_list, name='user_list'),
    path('add/', views.user_create, name='user_create'),
    path('<int:pk>/edit/', views.user_update, name='user_update'),
    path('<int:pk>/delete/', views.user_delete, name='user_delete'),
    path('backup/', views.backup_database, name='backup_database'),
    path('restore/', views.restore_database, name='restore_database'),
]
