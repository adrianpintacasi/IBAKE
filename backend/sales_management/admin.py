from django.contrib import admin
from .models import SalesOrder, SalesOrderItem

# Register your models here.
admin.site.register(SalesOrder)
admin.site.register(SalesOrderItem)
