from django.db import models
from django.core.validators import MinValueValidator
from decimal import Decimal
# from django.contrib.auth.models import AbstractUser, Group, Permission  # Not needed for now
from django.contrib.contenttypes.models import ContentType

class Employee(models.Model):
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('inactive', 'Inactive'),
        ('on_leave', 'On Leave'),
    ]

    POSITION_CHOICES = [
        ('admin', 'Admin'),
        ('cashier', 'Cashier'),
        ('baker', 'Baker'),
        ('decorator', 'Decorator'),
        ('manager', 'Manager'),
    ]

    # Position-based permissions mapping
    POSITION_PERMISSIONS = {
        'admin': {
            'can_access_all': True,
            'can_manage_employees': True,
            'can_manage_inventory': True,
            'can_manage_sales': True,
            'can_manage_accounting': True,
            'can_manage_customers': True,
            'can_view_reports': True,
        },
        'manager': {
            'can_access_all': False,
            'can_manage_employees': True,
            'can_manage_inventory': True,
            'can_manage_sales': True,
            'can_manage_accounting': True,
            'can_manage_customers': True,
            'can_view_reports': True,
        },
        'cashier': {
            'can_access_all': False,
            'can_manage_employees': False,
            'can_manage_inventory': False,
            'can_manage_sales': True,
            'can_manage_accounting': False,
            'can_manage_customers': True,
            'can_view_reports': False,
        },
        'baker': {
            'can_access_all': False,
            'can_manage_employees': False,
            'can_manage_inventory': True,  # Can manage production/recipes
            'can_manage_sales': False,
            'can_manage_accounting': False,
            'can_manage_customers': False,
            'can_view_reports': False,
        },
        'decorator': {
            'can_access_all': False,
            'can_manage_employees': False,
            'can_manage_inventory': True,  # Can manage production/recipes
            'can_manage_sales': False,
            'can_manage_accounting': False,
            'can_manage_customers': False,
            'can_view_reports': False,
        }
    }

    employee_id = models.CharField(max_length=20, unique=True)
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    position = models.CharField(max_length=20, choices=POSITION_CHOICES)
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=20, blank=True)
    address = models.TextField(blank=True)
    hire_date = models.DateField(null=True, blank=True)
    salary = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(Decimal('0.01'))])
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active')
    notes = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Employee'
        verbose_name_plural = 'Employees'
        ordering = ['employee_id']

    def __str__(self):
        return f"{self.employee_id} - {self.first_name} {self.last_name}"

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}"

    def get_permissions(self):
        """Get permissions based on position"""
        return self.POSITION_PERMISSIONS.get(self.position, {})

    def has_permission(self, permission_name):
        """Check if employee has specific permission"""
        permissions = self.get_permissions()
        return permissions.get(permission_name, False) or permissions.get('can_access_all', False)

    def save(self, *args, **kwargs):
        if not self.employee_id:
            # Generate employee ID based on position and sequence
            prefix = self.position[:3].upper()
            last_employee = Employee.objects.filter(
                position=self.position
            ).order_by('-employee_id').first()
            
            if last_employee:
                last_number = int(last_employee.employee_id[-4:])
                new_number = last_number + 1
            else:
                new_number = 1
                
            self.employee_id = f"{prefix}{new_number:04d}"
        
        super().save(*args, **kwargs)


# EmployeeUser model commented out due to migration conflicts# Will use standard Django User model instead# class EmployeeUser(AbstractUser):#     """Custom User model linked to Employee"""#     employee = models.OneToOneField(Employee, on_delete=models.CASCADE, null=True, blank=True)#     #     class Meta:#         verbose_name = 'Employee User'#         verbose_name_plural = 'Employee Users'#     #     def get_employee_permissions(self):#         """Get permissions from linked employee"""#         if self.employee:#             return self.employee.get_permissions()#         return {}#     #     def has_employee_permission(self, permission_name):#         """Check if user has specific employee permission"""#         if self.is_superuser:#             return True#         if self.employee:#             return self.employee.has_permission(permission_name)#         return False# #     @property#     def employee_position(self):#         """Get employee position"""#         if self.employee:#             return self.employee.position#         return None# #     @property#     def employee_full_name(self):#         """Get employee full name"""#         if self.employee:#             return self.employee.full_name#         return self.username 