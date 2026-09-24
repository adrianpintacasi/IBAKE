from django.db import models
from django.utils import timezone
from core.datetime_utils import get_current_date, get_current_datetime


class Customer(models.Model):
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=20, blank=True)
    address = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    added_by = models.ForeignKey('employee.Employee', on_delete=models.SET_NULL, null=True, blank=True, help_text="Employee who added this customer")
    created_at = models.DateTimeField(default=get_current_datetime)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f'{self.first_name} {self.last_name}'

    @property
    def full_name(self):
        return f'{self.first_name} {self.last_name}'
