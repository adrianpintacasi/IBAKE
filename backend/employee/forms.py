from django import forms
from .models import Employee

class EmployeeForm(forms.ModelForm):
    class Meta:
        model = Employee
        fields = ['first_name', 'last_name', 'position', 'email', 'phone', 'address', 'hire_date', 'salary', 'status', 'notes', 'is_active']
        widgets = {
            'address': forms.Textarea(attrs={'rows': 2}),
            'notes': forms.Textarea(attrs={'rows': 2}),
            'hire_date': forms.DateInput(attrs={'type': 'date'}),
        } 