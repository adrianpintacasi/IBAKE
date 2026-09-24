from django.db import models
from django.conf import settings
from django.core.validators import MinValueValidator
from decimal import Decimal

# Chart of Accounts Configuration
ACCOUNT_TYPES = [
    ('ASSET', 'Asset'),
    ('LIABILITY', 'Liability'),
    ('EQUITY', 'Equity'),
    ('REVENUE', 'Revenue'),
    ('EXPENSE', 'Expense'),
]

NORMAL_BALANCE_CHOICES = [
    ('DEBIT', 'Debit'),
    ('CREDIT', 'Credit'),
]

PAYMENT_METHOD_CHOICES = [
    ('CASH', 'Cash'),
    ('BANK', 'Bank Transfer'),
]

class Account(models.Model):
    """Chart of Accounts"""
    code = models.CharField(max_length=10, unique=True)
    name = models.CharField(max_length=100)
    account_type = models.CharField(max_length=20, choices=ACCOUNT_TYPES)
    normal_balance = models.CharField(max_length=6, choices=NORMAL_BALANCE_CHOICES)
    auto_calculate = models.BooleanField(default=False, help_text="Automatically calculated from system data")
    manual_balance = models.DecimalField(max_digits=12, decimal_places=2, default=0, help_text="Manual balance for non-auto accounts")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['code']
    
    def __str__(self):
        return f"{self.code} - {self.name}"
    
    def get_current_balance(self):
        """Get current balance for this account"""
        if self.auto_calculate:
            return self._calculate_auto_balance()
        else:
            return self.manual_balance
    
    def _calculate_auto_balance(self):
        """Calculate balance from transactions"""
        from django.db.models import Sum
        
        debits = self.transaction_set.aggregate(
            total=Sum('debit_amount')
        )['total'] or Decimal('0')
        
        credits = self.transaction_set.aggregate(
            total=Sum('credit_amount')
        )['total'] or Decimal('0')
        
        if self.normal_balance == 'DEBIT':
            return debits - credits
        else:
            return credits - debits

class JournalEntry(models.Model):
    """Journal Entry header"""
    entry_number = models.CharField(max_length=20, unique=True, default='AUTO')
    date = models.DateField()
    description = models.TextField()
    reference_type = models.CharField(max_length=50, null=True, blank=True, 
                                    help_text="Type: sales_order, production, payroll, utilities, etc.")
    reference_id = models.PositiveIntegerField(null=True, blank=True,
                                             help_text="ID of the referenced object")
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-date', '-entry_number']
        verbose_name_plural = "Journal Entries"
    
    def __str__(self):
        return f"JE-{self.entry_number} - {self.description[:50]}"
    
    def get_total_debits(self):
        return self.transaction_set.aggregate(
            total=models.Sum('debit_amount')
        )['total'] or Decimal('0')
    
    def get_total_credits(self):
        return self.transaction_set.aggregate(
            total=models.Sum('credit_amount')
        )['total'] or Decimal('0')
    
    def is_balanced(self):
        return self.get_total_debits() == self.get_total_credits()

class Transaction(models.Model):
    """Individual transaction lines within a journal entry"""
    journal_entry = models.ForeignKey(JournalEntry, on_delete=models.CASCADE)
    account = models.ForeignKey(Account, on_delete=models.CASCADE)
    debit_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0,
                                     validators=[MinValueValidator(Decimal('0'))])
    credit_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0,
                                      validators=[MinValueValidator(Decimal('0'))])
    description = models.CharField(max_length=200, blank=True)
    
    class Meta:
        ordering = ['journal_entry', 'id']
    
    def __str__(self):
        amount = self.debit_amount if self.debit_amount > 0 else self.credit_amount
        dr_cr = "Dr" if self.debit_amount > 0 else "Cr"
        return f"{self.account.name} - {dr_cr} ₱{amount}"

class PayrollEntry(models.Model):
    """Payroll transactions"""
    employee = models.ForeignKey('employee.Employee', on_delete=models.CASCADE)
    pay_period_start = models.DateField()
    pay_period_end = models.DateField()
    basic_salary = models.DecimalField(max_digits=10, decimal_places=2,
                                     validators=[MinValueValidator(Decimal('0'))])
    overtime_pay = models.DecimalField(max_digits=10, decimal_places=2, default=0,
                                     validators=[MinValueValidator(Decimal('0'))])
    total_pay = models.DecimalField(max_digits=10, decimal_places=2, editable=False)
    payment_date = models.DateField()
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHOD_CHOICES, default='CASH')
    notes = models.TextField(blank=True)
    journal_entry = models.ForeignKey(JournalEntry, on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-payment_date']
        unique_together = ['employee', 'pay_period_start', 'pay_period_end']
    
    def save(self, *args, **kwargs):
        self.total_pay = self.basic_salary + self.overtime_pay
        super().save(*args, **kwargs)
    
    def __str__(self):
        return f"Payroll - {self.employee.full_name} ({self.pay_period_start} to {self.pay_period_end})"

class UtilityEntry(models.Model):
    """Utilities and other expense transactions"""
    UTILITY_TYPES = [
        ('ELECTRICITY', 'Electricity'),
        ('WATER', 'Water'),
        ('INTERNET', 'Internet'),
        ('RENT', 'Rent'),
        ('MAINTENANCE', 'Maintenance'),
        ('SUPPLIES', 'Office Supplies'),
        ('OTHER', 'Other'),
    ]
    
    utility_type = models.CharField(max_length=20, choices=UTILITY_TYPES)
    description = models.CharField(max_length=200)
    amount = models.DecimalField(max_digits=10, decimal_places=2,
                               validators=[MinValueValidator(Decimal('0.01'))])
    billing_date = models.DateField()
    payment_date = models.DateField()
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHOD_CHOICES, default='CASH')
    notes = models.TextField(blank=True)
    journal_entry = models.ForeignKey(JournalEntry, on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-payment_date']
    
    def __str__(self):
        return f"{self.get_utility_type_display()} - ₱{self.amount} ({self.payment_date})"

class CashTransaction(models.Model):
    """Direct cash transactions (for owner's equity, equipment purchases, etc.)"""
    TRANSACTION_TYPES = [
        ('OWNER_INVESTMENT', "Owner's Investment"),
        ('OWNER_WITHDRAWAL', "Owner's Withdrawal"),
        ('EQUIPMENT_PURCHASE', 'Equipment Purchase'),
        ('LOAN_RECEIVED', 'Loan Received'),
        ('LOAN_PAYMENT', 'Loan Payment'),
        ('OTHER_INCOME', 'Other Income'),
        ('OTHER_EXPENSE', 'Other Expense'),
    ]
    
    transaction_type = models.CharField(max_length=30, choices=TRANSACTION_TYPES)
    description = models.CharField(max_length=200)
    amount = models.DecimalField(max_digits=12, decimal_places=2,
                               validators=[MinValueValidator(Decimal('0.01'))])
    transaction_date = models.DateField()
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHOD_CHOICES, default='CASH')
    notes = models.TextField(blank=True)
    journal_entry = models.ForeignKey(JournalEntry, on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-transaction_date']
    
    def __str__(self):
        return f"{self.get_transaction_type_display()} - ₱{self.amount} ({self.transaction_date})" 