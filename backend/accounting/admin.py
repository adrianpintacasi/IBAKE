from django.contrib import admin
from .models import (
    Account, JournalEntry, Transaction, PayrollEntry, 
    UtilityEntry, CashTransaction
)

@admin.register(Account)
class AccountAdmin(admin.ModelAdmin):
    list_display = ['code', 'name', 'account_type', 'normal_balance', 'auto_calculate', 'is_active']
    list_filter = ['account_type', 'normal_balance', 'auto_calculate', 'is_active']
    search_fields = ['code', 'name']
    ordering = ['account_type', 'code']

class TransactionInline(admin.TabularInline):
    model = Transaction
    extra = 2

@admin.register(JournalEntry)
class JournalEntryAdmin(admin.ModelAdmin):
    list_display = ['entry_number', 'date', 'description', 'reference_type', 'created_at']
    list_filter = ['reference_type', 'date']
    search_fields = ['entry_number', 'description']
    ordering = ['-date', '-entry_number']
    inlines = [TransactionInline]

@admin.register(PayrollEntry)
class PayrollEntryAdmin(admin.ModelAdmin):
    list_display = ['employee', 'pay_period_start', 'pay_period_end', 'total_pay', 'payment_date']
    list_filter = ['payment_date', 'payment_method']
    search_fields = ['employee__name']
    ordering = ['-payment_date']

@admin.register(UtilityEntry)
class UtilityEntryAdmin(admin.ModelAdmin):
    list_display = ['utility_type', 'description', 'amount', 'payment_date']
    list_filter = ['utility_type', 'payment_date', 'payment_method']
    search_fields = ['description']
    ordering = ['-payment_date']

@admin.register(CashTransaction)
class CashTransactionAdmin(admin.ModelAdmin):
    list_display = ['transaction_type', 'description', 'amount', 'transaction_date']
    list_filter = ['transaction_type', 'transaction_date', 'payment_method']
    search_fields = ['description']
    ordering = ['-transaction_date'] 