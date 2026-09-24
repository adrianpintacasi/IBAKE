from django.urls import path
from . import views

app_name = 'core'

urlpatterns = [
    path('', views.HomeView.as_view(), name='home'),
    path('dashboard/', views.DashboardView.as_view(), name='dashboard'),
    path('export-grocery-list/', views.export_grocery_list, name='export_grocery_list'),
    path('export-out-of-stock/', views.export_out_of_stock, name='export_out_of_stock'),
    path('export-low-stock/', views.export_low_stock, name='export_low_stock'),
] 