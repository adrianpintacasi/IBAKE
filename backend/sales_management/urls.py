from django.urls import path
from . import views

app_name = 'sales_management'

urlpatterns = [
    path('', views.SalesOrderListView.as_view(), name='sales_order_list'),
    path('add/', views.SalesOrderCreateView.as_view(), name='sales_order_add'),
    path('ajax/add_customer/', views.ajax_add_customer, name='ajax_add_customer'),
    path('ajax/add_payment/', views.ajax_add_payment, name='ajax_add_payment'),
    path('ajax/check_inventory/', views.ajax_check_inventory, name='ajax_check_inventory'),
    path('ajax/order_details/<int:pk>/', views.ajax_order_details, name='ajax_order_details'),
    path('ajax/order_delete/<int:pk>/', views.ajax_order_delete, name='ajax_order_delete'),
] 