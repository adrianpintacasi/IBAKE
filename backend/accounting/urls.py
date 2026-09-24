from django.urls import path
from . import views

app_name = 'accounting'

urlpatterns = [
    # Dashboard
    path('', views.accounting_dashboard, name='dashboard'),
    
    # Trial Balance
    path('trial-balance/', views.trial_balance_view, name='trial_balance'),
    path('trial-balance/export-csv/', views.trial_balance_export_csv, name='trial_balance_export_csv'),
    
    # Accounts Management
    path('accounts/', views.AccountListView.as_view(), name='account_list'),
    path('accounts/add/', views.AccountCreateView.as_view(), name='account_create'),
    path('accounts/<int:pk>/edit/', views.AccountUpdateView.as_view(), name='account_update'),
    
    # Payroll
    path('payroll/', views.PayrollListView.as_view(), name='payroll_list'),
    path('payroll/add/', views.PayrollCreateView.as_view(), name='payroll_create'),
    
    # Utilities
    path('utilities/', views.UtilityListView.as_view(), name='utility_list'),
    path('utilities/add/', views.UtilityCreateView.as_view(), name='utility_create'),
    
    # Cash Transactions
    path('cash-transactions/', views.CashTransactionListView.as_view(), name='cash_transaction_list'),
    path('cash-transactions/add/', views.CashTransactionCreateView.as_view(), name='cash_transaction_create'),
    path('cash-transactions/<int:pk>/', views.CashTransactionDetailView.as_view(), name='cash_transaction_detail'),
    
    # Journal Entries
    path('journal-entries/', views.JournalEntryListView.as_view(), name='journal_entry_list'),
    path('journal-entries/add/', views.journal_entry_create, name='journal_entry_create'),
    path('journal-entries/<int:pk>/', views.JournalEntryDetailView.as_view(), name='journal_entry_detail'),
    path('journal-entries/export-csv/', views.journal_entry_export_csv, name='journal_entry_export_csv'),
    
    # Financial Reports
    path('reports/cash-flow-statement/', views.cash_flow_statement, name='cash_flow_statement'),
    path('reports/accounts-receivable-aging/', views.accounts_receivable_aging, name='accounts_receivable_aging'),
    path('reports/inventory-valuation/', views.inventory_valuation_report, name='inventory_valuation_report'),
] 