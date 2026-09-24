from django.urls import path
from .views import CustomerListView, CustomerCreateView, CustomerUpdateView, CustomerDeleteView

app_name = 'customer_management'

urlpatterns = [
    path('customers/', CustomerListView.as_view(), name='customer_list'),
    path('customers/add/', CustomerCreateView.as_view(), name='customer_add'),
    path('customers/<int:pk>/edit/', CustomerUpdateView.as_view(), name='customer_edit'),
    path('customers/<int:pk>/delete/', CustomerDeleteView.as_view(), name='customer_delete'),
] 