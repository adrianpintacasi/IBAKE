from django import forms
from .models import SalesOrder, SalesOrderItem

class SalesOrderForm(forms.ModelForm):
    class Meta:
        model = SalesOrder
        fields = ['customer_name', 'customer_address', 'employee', 'status', 'total_amount', 'amount_paid']
        widgets = {
            'customer_address': forms.Textarea(attrs={'rows': 3}),
        }

class SalesOrderItemForm(forms.ModelForm):
    class Meta:
        model = SalesOrderItem
        fields = ['product', 'quantity', 'unit_price', 'discount']
        widgets = {
            'quantity': forms.NumberInput(attrs={'min': 1}),
            'unit_price': forms.NumberInput(attrs={'step': '0.01'}),
            'discount': forms.NumberInput(attrs={'min': 0, 'max': 100, 'step': '0.01'}),
        } 