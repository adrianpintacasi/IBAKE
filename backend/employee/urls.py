from django.urls import path
from .views import EmployeeListView, EmployeeCreateView, EmployeeUpdateView, EmployeeDeleteView

app_name = 'employee'

urlpatterns = [
    path('employees/', EmployeeListView.as_view(), name='employee_list'),
    path('employees/add/', EmployeeCreateView.as_view(), name='employee_add'),
    path('employees/<int:pk>/edit/', EmployeeUpdateView.as_view(), name='employee_edit'),
    path('employees/<int:pk>/delete/', EmployeeDeleteView.as_view(), name='employee_delete'),
] 