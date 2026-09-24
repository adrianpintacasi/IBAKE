from functools import wraps
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.contrib.auth.mixins import UserPassesTestMixin
from django.shortcuts import redirect
from django.contrib import messages
from django.urls import reverse_lazy


def employee_permission_required(permission_name):
    """
    Decorator that checks if user has the required employee permission
    """
    def decorator(view_func):
        @wraps(view_func)
        @login_required
        def _wrapped_view(request, *args, **kwargs):
            if request.user.has_employee_permission(permission_name):
                return view_func(request, *args, **kwargs)
            else:
                messages.error(request, f"You don't have permission to access this area. Required permission: {permission_name}")
                return redirect('core:dashboard')
        return _wrapped_view
    return decorator


class EmployeePermissionMixin(UserPassesTestMixin):
    """
    Mixin that checks if user has the required employee permission
    """
    permission_required = None
    permission_denied_message = "You don't have permission to access this area."
    login_url = reverse_lazy('login')
    
    def test_func(self):
        if not self.permission_required:
            return True
        return self.request.user.has_employee_permission(self.permission_required)
    
    def handle_no_permission(self):
        if self.request.user.is_authenticated:
            messages.error(self.request, self.permission_denied_message)
            return redirect('core:dashboard')
        return super().handle_no_permission()


class AdminOrManagerMixin(EmployeePermissionMixin):
    """Mixin that allows access only to Admin or Manager roles"""
    def test_func(self):
        user = self.request.user
        return (user.is_authenticated and 
                (user.employee_position in ['admin', 'manager'] or user.is_superuser))


class AdminOnlyMixin(EmployeePermissionMixin):
    """Mixin that allows access only to Admin role"""
    def test_func(self):
        user = self.request.user
        return (user.is_authenticated and 
                (user.employee_position == 'admin' or user.is_superuser))


# Position-specific mixins
class CanManageEmployeesMixin(EmployeePermissionMixin):
    permission_required = 'can_manage_employees'
    permission_denied_message = "You don't have permission to manage employees."


class CanManageInventoryMixin(EmployeePermissionMixin):
    permission_required = 'can_manage_inventory'
    permission_denied_message = "You don't have permission to manage inventory."


class CanManageSalesMixin(EmployeePermissionMixin):
    permission_required = 'can_manage_sales'
    permission_denied_message = "You don't have permission to manage sales."


class CanManageAccountingMixin(EmployeePermissionMixin):
    permission_required = 'can_manage_accounting'
    permission_denied_message = "You don't have permission to manage accounting."


class CanManageCustomersMixin(EmployeePermissionMixin):
    permission_required = 'can_manage_customers'
    permission_denied_message = "You don't have permission to manage customers."


class CanViewReportsMixin(EmployeePermissionMixin):
    permission_required = 'can_view_reports'
    permission_denied_message = "You don't have permission to view reports." 