from django.contrib import admin
from .models import Customer

# Register your models here.

@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    list_display = ['first_name', 'last_name', 'email', 'phone', 'added_by', 'is_active', 'created_at']
    list_filter = ['is_active', 'added_by', 'created_at']
    search_fields = ['first_name', 'last_name', 'email', 'phone']
    readonly_fields = ['created_at', 'updated_at']
    ordering = ['-created_at']
