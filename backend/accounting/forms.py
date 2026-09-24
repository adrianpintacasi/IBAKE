from django import forms
from django.forms import inlineformset_factory
from .models import (
    Account, JournalEntry, Transaction, PayrollEntry, 
    UtilityEntry, CashTransaction, ACCOUNT_TYPES
)
from employee.models import Employee
from decimal import Decimal

class PayrollEntryForm(forms.ModelForm):
    class Meta:
        model = PayrollEntry
        fields = [
            'employee', 'pay_period_start', 'pay_period_end',
            'basic_salary', 'overtime_pay', 'payment_date', 
            'payment_method', 'notes'
        ]
        widgets = {
            'employee': forms.Select(attrs={'class': 'form-select'}),
            'pay_period_start': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'pay_period_end': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'basic_salary': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': '0'}),
            'overtime_pay': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': '0'}),
            'payment_date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'payment_method': forms.Select(attrs={'class': 'form-select'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['employee'].queryset = Employee.objects.filter(is_active=True)

class UtilityEntryForm(forms.ModelForm):
    class Meta:
        model = UtilityEntry
        fields = [
            'utility_type', 'description', 'amount', 
            'billing_date', 'payment_date', 'payment_method', 'notes'
        ]
        widgets = {
            'utility_type': forms.Select(attrs={'class': 'form-select'}),
            'description': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g., May 2025 Electricity Bill'}),
            'amount': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': '0.01'}),
            'billing_date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'payment_date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'payment_method': forms.Select(attrs={'class': 'form-select'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }

class CashTransactionForm(forms.ModelForm):
    class Meta:
        model = CashTransaction
        fields = [
            'transaction_type', 'description', 'amount',
            'transaction_date', 'payment_method', 'notes'
        ]
        widgets = {
            'transaction_type': forms.Select(attrs={'class': 'form-select'}),
            'description': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g., Initial capital investment'}),
            'amount': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': '0.01'}),
            'transaction_date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'payment_method': forms.Select(attrs={'class': 'form-select'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }

class AccountForm(forms.ModelForm):
    class Meta:
        model = Account
        fields = ['code', 'name', 'account_type', 'normal_balance', 'auto_calculate', 'manual_balance']
        widgets = {
            'code': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g., 1000'}),
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g., Cash in Bank'}),
            'account_type': forms.Select(attrs={'class': 'form-select'}),
            'normal_balance': forms.Select(attrs={'class': 'form-select'}),
            'auto_calculate': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'manual_balance': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
        }

class JournalEntryForm(forms.ModelForm):
    class Meta:
        model = JournalEntry
        fields = ['entry_number', 'date', 'description']
        widgets = {
            'entry_number': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'AUTO'}),
            'date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Enter description for this journal entry...'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Set default date to today
        if not self.instance.pk:
            from core.datetime_utils import get_current_date
            self.fields['date'].initial = get_current_date()

class TransactionForm(forms.ModelForm):
    class Meta:
        model = Transaction
        fields = ['account', 'debit_amount', 'credit_amount', 'description']
        widgets = {
            'account': forms.Select(attrs={'class': 'form-select'}),
            'debit_amount': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': '0', 'placeholder': '0.00'}),
            'credit_amount': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': '0', 'placeholder': '0.00'}),
            'description': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Transaction description...'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Improve account queryset to show active accounts only
        self.fields['account'].queryset = Account.objects.filter(is_active=True).order_by('code')
        self.fields['account'].empty_label = "Select Account"
    
    def clean(self):
        cleaned_data = super().clean()
        debit_amount = cleaned_data.get('debit_amount', 0) or 0
        credit_amount = cleaned_data.get('credit_amount', 0) or 0
        
        # Ensure only debit OR credit is provided, not both
        if debit_amount > 0 and credit_amount > 0:
            raise forms.ValidationError("A transaction can have either a debit or credit amount, not both.")
        
        # Require that at least one amount is provided
        if debit_amount == 0 and credit_amount == 0:
            raise forms.ValidationError("A transaction must have either a debit or credit amount.")
        
        return cleaned_data

# Formset for Journal Entry Transactions
TransactionFormSet = inlineformset_factory(
    JournalEntry,
    Transaction,
    form=TransactionForm,
    extra=2,
    can_delete=True,
    min_num=2,
    validate_min=True
)

class TrialBalanceFilterForm(forms.Form):
    """Filter form for trial balance date selection"""
    as_of_date = forms.DateField(
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
        required=False,
        help_text="Leave blank for current date"
    )
    
    account_type = forms.ChoiceField(
        choices=[('', 'All Types')] + ACCOUNT_TYPES,
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'})
    )

class StockInPaymentForm(forms.Form):
    """Form to add payment information to existing Stock In entries"""
    payment_date = forms.DateField(
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
        help_text="Date when payment was made"
    )
    payment_method = forms.ChoiceField(
        choices=[('CASH', 'Cash'), ('BANK', 'Bank Transfer')],
        widget=forms.Select(attrs={'class': 'form-select'}),
        initial='CASH'
    )
    notes = forms.CharField(
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        required=False,
        help_text="Additional notes about the payment"
    )

class JournalEntryFilterForm(forms.Form):
    """Filter form for journal entries"""
    search = forms.CharField(
        max_length=100,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Search by entry number or description...'
        })
    )
    
    reference_type = forms.ChoiceField(
        choices=[('', 'All Types')] + [
            ('stock_in', 'Stock In'),
            ('production', 'Production'),
            ('production_waste', 'Production Waste'),
            ('expired_goods', 'Expired Goods'),
            ('manual', 'Manual Entry'),
        ],
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    date_from = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'})
    )
    
    date_to = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'})
    ) 