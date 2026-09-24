from django import forms
from .models import Customer

class CustomerForm(forms.ModelForm):
    class Meta:
        model = Customer
        fields = ['first_name', 'last_name', 'email', 'phone', 'address', 'added_by', 'is_active']
        widgets = {
            'address': forms.Textarea(attrs={'rows': 3}),
        } 