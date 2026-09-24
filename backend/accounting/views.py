from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import ListView, CreateView, UpdateView, DetailView
from django.contrib import messages
from django.http import JsonResponse, HttpResponse
from django.db import transaction
from django.utils import timezone
from django.db import models
from django.db.models import Q
from decimal import Decimal
import csv
from core.datetime_utils import get_current_date, get_current_datetime, format_datetime_for_display

from .models import (
    Account, JournalEntry, Transaction, PayrollEntry, 
    UtilityEntry, CashTransaction
)
from .forms import (
    AccountForm, PayrollEntryForm, UtilityEntryForm, 
    CashTransactionForm, JournalEntryForm, TransactionFormSet,
    TrialBalanceFilterForm
)
from .utils import (
    get_trial_balance_data, create_journal_entry, 
    generate_journal_entry_number
)

@login_required
def accounting_dashboard(request):
    """Redirect to main dashboard"""
    from django.shortcuts import redirect
    return redirect('core:dashboard')

@login_required
def trial_balance_view(request):
    """Display trial balance"""
    form = TrialBalanceFilterForm(request.GET or None)
    
    as_of_date = None
    account_type = None
    if form.is_valid():
        as_of_date = form.cleaned_data.get('as_of_date')
        account_type = form.cleaned_data.get('account_type')
    
    trial_balance_data = get_trial_balance_data(as_of_date, account_type)
    
    total_debits = sum(item['debit_amount'] for item in trial_balance_data)
    total_credits = sum(item['credit_amount'] for item in trial_balance_data)
    
    context = {
        'form': form,
        'trial_balance_data': trial_balance_data,
        'total_debits': total_debits,
        'total_credits': total_credits,
        'is_balanced': total_debits == total_credits,
        'difference': total_debits - total_credits,
    }
    return render(request, 'accounting/trial_balance.html', context)

@login_required
def trial_balance_export_csv(request):
    """Export trial balance to CSV"""
    as_of_date = request.GET.get('as_of_date')
    account_type = request.GET.get('account_type')
    trial_balance_data = get_trial_balance_data(as_of_date, account_type)
    
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="trial_balance_{as_of_date or get_current_date()}.csv"'
    
    writer = csv.writer(response)
    writer.writerow(['Account Code', 'Account Name', 'Debit', 'Credit'])
    
    total_debits = Decimal('0')
    total_credits = Decimal('0')
    
    for item in trial_balance_data:
        writer.writerow([
            item['code'],
            item['name'],
            item['debit_amount'],
            item['credit_amount']
        ])
        total_debits += item['debit_amount']
        total_credits += item['credit_amount']
    
    writer.writerow(['', 'TOTALS', total_debits, total_credits])
    
    return response

class AccountListView(LoginRequiredMixin, ListView):
    model = Account
    template_name = 'accounting/account_list.html'
    context_object_name = 'accounts'
    ordering = ['account_type', 'code']

class AccountCreateView(LoginRequiredMixin, CreateView):
    model = Account
    form_class = AccountForm
    template_name = 'accounting/account_form.html'
    success_url = '/accounting/accounts/'

class AccountUpdateView(LoginRequiredMixin, UpdateView):
    model = Account
    form_class = AccountForm
    template_name = 'accounting/account_form.html'
    success_url = '/accounting/accounts/'

class PayrollListView(LoginRequiredMixin, ListView):
    model = PayrollEntry
    template_name = 'accounting/payroll_list.html'
    context_object_name = 'payroll_entries'
    ordering = ['-payment_date']
    
    def get_queryset(self):
        queryset = super().get_queryset()
        
        search = self.request.GET.get('search')
        payment_method = self.request.GET.get('payment_method')
        date_from = self.request.GET.get('date_from')
        
        if search:
            queryset = queryset.filter(employee__full_name__icontains=search)
        
        if payment_method:
            queryset = queryset.filter(payment_method=payment_method)
        
        if date_from:
            queryset = queryset.filter(payment_date__gte=date_from)
        
        return queryset

class PayrollCreateView(LoginRequiredMixin, CreateView):
    model = PayrollEntry
    form_class = PayrollEntryForm
    template_name = 'accounting/payroll_form.html'
    success_url = '/accounting/payroll/'
    
    def form_valid(self, form):
        with transaction.atomic():
            response = super().form_valid(form)
            
            payroll_entry = self.object
            journal_entry = create_journal_entry(
                description=f"Payroll - {payroll_entry.employee.full_name} ({payroll_entry.pay_period_start} to {payroll_entry.pay_period_end})",
                transactions=[
                    {
                        'account_code': 'PAYROLL',
                        'debit': payroll_entry.total_pay,
                        'credit': 0,
                        'description': f"Payroll expense for {payroll_entry.employee.full_name}"
                    },
                    {
                        'account_code': 'CASH',
                        'debit': 0,
                        'credit': payroll_entry.total_pay,
                        'description': f"Cash payment to {payroll_entry.employee.full_name}"
                    }
                ],
                reference_type='payroll',
                reference_id=payroll_entry.id,
                entry_date=payroll_entry.payment_date
            )
            
            payroll_entry.journal_entry = journal_entry
            payroll_entry.save()
            
            messages.success(self.request, f'Payroll entry created and journal entry {journal_entry.entry_number} generated.')
        
        return response

class UtilityListView(LoginRequiredMixin, ListView):
    model = UtilityEntry
    template_name = 'accounting/utility_list.html'
    context_object_name = 'utility_entries'
    ordering = ['-payment_date']
    
    def get_queryset(self):
        queryset = super().get_queryset()
        
        search = self.request.GET.get('search')
        utility_type = self.request.GET.get('utility_type')
        payment_method = self.request.GET.get('payment_method')
        
        if search:
            queryset = queryset.filter(description__icontains=search)
        
        if utility_type:
            queryset = queryset.filter(utility_type=utility_type)
        
        if payment_method:
            queryset = queryset.filter(payment_method=payment_method)
        
        return queryset

class UtilityCreateView(LoginRequiredMixin, CreateView):
    model = UtilityEntry
    form_class = UtilityEntryForm
    template_name = 'accounting/utility_form.html'
    success_url = '/accounting/utilities/'
    
    def form_valid(self, form):
        with transaction.atomic():
            response = super().form_valid(form)
            
            utility_entry = self.object
            journal_entry = create_journal_entry(
                description=f"{utility_entry.get_utility_type_display()} - {utility_entry.description}",
                transactions=[
                    {
                        'account_code': 'UTILITIES',
                        'debit': utility_entry.amount,
                        'credit': 0,
                        'description': f"{utility_entry.get_utility_type_display()} expense"
                    },
                    {
                        'account_code': 'CASH',
                        'debit': 0,
                        'credit': utility_entry.amount,
                        'description': f"Cash payment for {utility_entry.get_utility_type_display()}"
                    }
                ],
                reference_type='utility',
                reference_id=utility_entry.id,
                entry_date=utility_entry.payment_date
            )
            
            utility_entry.journal_entry = journal_entry
            utility_entry.save()
            
            messages.success(self.request, f'Utility entry created and journal entry {journal_entry.entry_number} generated.')
        
        return response

class CashTransactionListView(LoginRequiredMixin, ListView):
    model = CashTransaction
    template_name = 'accounting/cash_transaction_list.html'
    context_object_name = 'transactions'
    ordering = ['-transaction_date']
    
    def get_queryset(self):
        queryset = super().get_queryset()
        
        search = self.request.GET.get('search')
        transaction_type = self.request.GET.get('transaction_type')
        payment_method = self.request.GET.get('payment_method')
        
        if search:
            queryset = queryset.filter(description__icontains=search)
        
        if transaction_type:
            queryset = queryset.filter(transaction_type=transaction_type)
        
        if payment_method:
            queryset = queryset.filter(payment_method=payment_method)
        
        return queryset

class CashTransactionCreateView(LoginRequiredMixin, CreateView):
    model = CashTransaction
    form_class = CashTransactionForm
    template_name = 'accounting/add_cash_transaction.html'
    success_url = '/accounting/cash-transactions/'
    
    def form_valid(self, form):
        with transaction.atomic():
            response = super().form_valid(form)
            
            cash_transaction = self.object
            
            # Determine accounts based on transaction type
            if cash_transaction.transaction_type == 'OWNER_INVESTMENT':
                transactions = [
                    {'account_code': 'CASH', 'debit': cash_transaction.amount, 'credit': 0},
                    {'account_code': 'OWNER_EQ', 'debit': 0, 'credit': cash_transaction.amount}
                ]
            elif cash_transaction.transaction_type == 'OWNER_WITHDRAWAL':
                transactions = [
                    {'account_code': 'OWNER_EQ', 'debit': cash_transaction.amount, 'credit': 0},
                    {'account_code': 'CASH', 'debit': 0, 'credit': cash_transaction.amount}
                ]
            elif cash_transaction.transaction_type == 'EQUIPMENT_PURCHASE':
                transactions = [
                    {'account_code': 'EQUIPMENT', 'debit': cash_transaction.amount, 'credit': 0},
                    {'account_code': 'CASH', 'debit': 0, 'credit': cash_transaction.amount}
                ]
            else:
                if 'INCOME' in cash_transaction.transaction_type:
                    transactions = [
                        {'account_code': 'CASH', 'debit': cash_transaction.amount, 'credit': 0},
                        {'account_code': 'OTHER_INC', 'debit': 0, 'credit': cash_transaction.amount}
                    ]
                else:
                    transactions = [
                        {'account_code': 'OTHER_EXP', 'debit': cash_transaction.amount, 'credit': 0},
                        {'account_code': 'CASH', 'debit': 0, 'credit': cash_transaction.amount}
                    ]
            
            journal_entry = create_journal_entry(
                description=f"{cash_transaction.get_transaction_type_display()} - {cash_transaction.description}",
                transactions=transactions,
                reference_type='cash_transaction',
                reference_id=cash_transaction.id,
                entry_date=cash_transaction.transaction_date
            )
            
            cash_transaction.journal_entry = journal_entry
            cash_transaction.save()
            
            messages.success(self.request, f'Cash transaction recorded and journal entry {journal_entry.entry_number} generated.')
        
        return response

class CashTransactionDetailView(LoginRequiredMixin, DetailView):
    model = CashTransaction
    template_name = 'accounting/cash_transaction_detail.html'
    context_object_name = 'transaction'

class JournalEntryListView(LoginRequiredMixin, ListView):
    model = JournalEntry
    template_name = 'accounting/journal_entry_list.html'
    context_object_name = 'journal_entries'
    ordering = ['-date', '-entry_number']
    paginate_by = 25
    
    def get_queryset(self):
        queryset = super().get_queryset()
        
        search = self.request.GET.get('search')
        reference_type = self.request.GET.get('reference_type')
        date_from = self.request.GET.get('date_from')
        date_to = self.request.GET.get('date_to')
        
        if search:
            queryset = queryset.filter(
                Q(entry_number__icontains=search) |
                Q(description__icontains=search)
            )
        
        if reference_type:
            if reference_type == 'manual':
                queryset = queryset.filter(reference_type__isnull=True)
            else:
                queryset = queryset.filter(reference_type=reference_type)
        
        if date_from:
            queryset = queryset.filter(date__gte=date_from)
        
        if date_to:
            queryset = queryset.filter(date__lte=date_to)
        
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        from .forms import JournalEntryFilterForm
        context['filter_form'] = JournalEntryFilterForm(self.request.GET or None)
        
        return context

class JournalEntryDetailView(LoginRequiredMixin, DetailView):
    model = JournalEntry
    template_name = 'accounting/journal_entry_detail.html'
    context_object_name = 'journal_entry'

@login_required
def journal_entry_create(request):
    """Create manual journal entry with transactions"""
    if request.method == 'POST':
        form = JournalEntryForm(request.POST)
        formset = TransactionFormSet(request.POST)
        
        if form.is_valid() and formset.is_valid():
            with transaction.atomic():
                journal_entry = form.save(commit=False)
                journal_entry.created_by = request.user
                if not journal_entry.entry_number or journal_entry.entry_number == 'AUTO':
                    journal_entry.entry_number = generate_journal_entry_number()
                journal_entry.save()
                
                formset.instance = journal_entry
                transactions = formset.save()
                    
                if journal_entry.is_balanced():
                    messages.success(request, f'Journal entry {journal_entry.entry_number} created successfully.')
                    return redirect('accounting:journal_entry_list')
                else:
                    journal_entry.delete()
                    messages.error(request, 'Journal entry is not balanced. Please ensure total debits equal total credits.')
        else:
            if not form.is_valid():
                messages.error(request, 'Please correct the errors in the journal entry details.')
            if not formset.is_valid():
                messages.error(request, 'Please correct the errors in the transaction lines.')
    else:
        form = JournalEntryForm()
        formset = TransactionFormSet(queryset=Transaction.objects.none())
    
    context = {
        'form': form,
        'formset': formset,
    }
    return render(request, 'accounting/journal_entry_form.html', context)

@login_required
def cash_flow_statement(request):
    """Generate cash flow statement"""
    from .utils import (
        calculate_cash_balance, calculate_sales_revenue,
        calculate_material_purchases
    )
    from .models import PayrollEntry, UtilityEntry, CashTransaction
    from django.db.models import Sum
    from datetime import datetime, timedelta
    
    end_date = get_current_date()
    start_date = end_date.replace(day=1)
    
    if request.GET.get('start_date'):
        start_date = datetime.strptime(request.GET.get('start_date'), '%Y-%m-%d').date()
    if request.GET.get('end_date'):
        end_date = datetime.strptime(request.GET.get('end_date'), '%Y-%m-%d').date()
    
    sales_revenue = calculate_sales_revenue()
    material_purchases = calculate_material_purchases()
    
    payroll_payments = PayrollEntry.objects.filter(
        payment_date__range=[start_date, end_date]
    ).aggregate(total=Sum('total_pay'))['total'] or Decimal('0')
    
    utility_payments = UtilityEntry.objects.filter(
        payment_date__range=[start_date, end_date]
    ).aggregate(total=Sum('amount'))['total'] or Decimal('0')
    
    equipment_purchases = CashTransaction.objects.filter(
        transaction_type='EQUIPMENT_PURCHASE',
        transaction_date__range=[start_date, end_date]
    ).aggregate(total=Sum('amount'))['total'] or Decimal('0')
    
    owner_investments = CashTransaction.objects.filter(
        transaction_type='OWNER_INVESTMENT',
        transaction_date__range=[start_date, end_date]
    ).aggregate(total=Sum('amount'))['total'] or Decimal('0')
    
    owner_withdrawals = CashTransaction.objects.filter(
        transaction_type='OWNER_WITHDRAWAL',
        transaction_date__range=[start_date, end_date]
    ).aggregate(total=Sum('amount'))['total'] or Decimal('0')
    
    loan_received = CashTransaction.objects.filter(
        transaction_type='LOAN_RECEIVED',
        transaction_date__range=[start_date, end_date]
    ).aggregate(total=Sum('amount'))['total'] or Decimal('0')
    
    loan_payments = CashTransaction.objects.filter(
        transaction_type='LOAN_PAYMENT',
        transaction_date__range=[start_date, end_date]
    ).aggregate(total=Sum('amount'))['total'] or Decimal('0')
    
    operating_cash_flow = sales_revenue - material_purchases - payroll_payments - utility_payments
    investing_cash_flow = -equipment_purchases
    financing_cash_flow = owner_investments - owner_withdrawals + loan_received - loan_payments
    
    net_cash_flow = operating_cash_flow + investing_cash_flow + financing_cash_flow
    
    context = {
        'start_date': start_date,
        'end_date': end_date,
        'operating_activities': {
            'sales_revenue': sales_revenue,
            'material_purchases': material_purchases,
            'payroll_payments': payroll_payments,
            'utility_payments': utility_payments,
            'net_operating_cash_flow': operating_cash_flow,
        },
        'investing_activities': {
            'equipment_purchases': equipment_purchases,
            'net_investing_cash_flow': investing_cash_flow,
        },
        'financing_activities': {
            'owner_investments': owner_investments,
            'owner_withdrawals': owner_withdrawals,
            'loan_received': loan_received,
            'loan_payments': loan_payments,
            'net_financing_cash_flow': financing_cash_flow,
        },
        'net_cash_flow': net_cash_flow,
        'current_cash_balance': calculate_cash_balance(),
    }
    
    return render(request, 'accounting/cash_flow_statement.html', context)

@login_required
def accounts_receivable_aging(request):
    """Generate accounts receivable aging report"""
    try:
        from sales_management.models import SalesOrder
        from datetime import timedelta
        
        current_date = get_current_date()
        
        open_orders = SalesOrder.objects.filter(status='open').order_by('-order_date')
        
        aging_data = []
        total_current = Decimal('0')
        total_30_days = Decimal('0')
        total_60_days = Decimal('0')
        total_90_days = Decimal('0')
        total_over_90 = Decimal('0')
        
        for order in open_orders:
            days_outstanding = (current_date - order.order_date).days
            
            if days_outstanding <= 30:
                category = 'Current'
                total_current += order.total_amount
            elif days_outstanding <= 60:
                category = '31-60 Days'
                total_30_days += order.total_amount
            elif days_outstanding <= 90:
                category = '61-90 Days'
                total_60_days += order.total_amount
            else:
                category = 'Over 90 Days'
                total_over_90 += order.total_amount
            
            aging_data.append({
                'order': order,
                'days_outstanding': days_outstanding,
                'category': category,
            })
        
        context = {
            'aging_data': aging_data,
            'totals': {
                'current': total_current,
                '30_days': total_30_days,
                '60_days': total_60_days,
                '90_days': total_90_days,
                'over_90': total_over_90,
                'total': total_current + total_30_days + total_60_days + total_90_days + total_over_90,
            }
        }
        
        return render(request, 'accounting/accounts_receivable_aging.html', context)
    
    except ImportError:
        messages.error(request, 'Sales management module not available.')
        return redirect('accounting:dashboard')

@login_required
def inventory_valuation_report(request):
    """Generate inventory valuation report"""
    from .utils import (
        calculate_raw_materials_inventory,
        calculate_finished_goods_inventory,
        calculate_work_in_progress
    )
    
    try:
        from inventory.models import RawMaterial, RawMaterialMovement, FinishedGoodsInventory
        
        raw_materials_detail = []
        for material in RawMaterial.objects.all():
            available_stock = RawMaterialMovement.get_available_stock(material)
            if available_stock > 0:
                from inventory.models import StockInDetail
                latest_stock_in = StockInDetail.objects.filter(
                    material=material
                ).order_by('-created_at').first()
                
                price_per_unit = latest_stock_in.unit_price if latest_stock_in else material.unit_cost
                stock_in_units = material.from_base_unit(available_stock)
                total_value = stock_in_units * price_per_unit
                
                raw_materials_detail.append({
                    'material': material,
                    'quantity': stock_in_units,
                    'unit_price': price_per_unit,
                    'total_value': total_value,
                })
        
        finished_goods_detail = []
        for inventory in FinishedGoodsInventory.objects.all():
            available_stock = FinishedGoodsInventory.get_available_stock(inventory.product)
            if available_stock > 0:
                from .utils import calculate_product_cost
                cost_per_unit = calculate_product_cost(inventory.product)
                total_value = Decimal(str(available_stock)) * cost_per_unit
                
                finished_goods_detail.append({
                    'product': inventory.product,
                    'quantity': available_stock,
                    'unit_cost': cost_per_unit,
                    'total_value': total_value,
                })
        
        context = {
            'raw_materials_detail': raw_materials_detail,
            'finished_goods_detail': finished_goods_detail,
            'totals': {
                'raw_materials': calculate_raw_materials_inventory(),
                'finished_goods': calculate_finished_goods_inventory(),
                'work_in_progress': calculate_work_in_progress(),
                'total_inventory': (
                    calculate_raw_materials_inventory() + 
                    calculate_finished_goods_inventory() + 
                    calculate_work_in_progress()
                ),
            }
        }
        
        return render(request, 'accounting/inventory_valuation_report.html', context)
    
    except ImportError:
        messages.error(request, 'Inventory module not available.')
        return redirect('accounting:dashboard')

@login_required
def journal_entry_export_csv(request):
    """Export journal entries to CSV with applied filters"""
    queryset = JournalEntry.objects.all().order_by('-date', '-entry_number')
    
    search = request.GET.get('search')
    reference_type = request.GET.get('reference_type')
    date_from = request.GET.get('date_from')
    date_to = request.GET.get('date_to')
    
    if search:
        queryset = queryset.filter(
            Q(entry_number__icontains=search) |
            Q(description__icontains=search)
        )
    
    if reference_type:
        if reference_type == 'manual':
            queryset = queryset.filter(reference_type__isnull=True)
        else:
            queryset = queryset.filter(reference_type=reference_type)
    
    if date_from:
        queryset = queryset.filter(date__gte=date_from)
    
    if date_to:
        queryset = queryset.filter(date__lte=date_to)
    
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="journal_entries_{format_datetime_for_display(get_current_datetime(), "%Y%m%d_%H%M%S")}.csv"'
    
    writer = csv.writer(response)
    
    writer.writerow([
        'Entry Number',
        'Date',
        'Description',
        'Reference Type',
        'Total Debits',
        'Total Credits',
        'Is Balanced',
        'Created At',
        'Created By'
    ])
    
    for entry in queryset:
        writer.writerow([
            entry.entry_number,
            entry.date.strftime('%Y-%m-%d'),
            entry.description,
            entry.reference_type if entry.reference_type else 'Manual',
            float(entry.get_total_debits()),
            float(entry.get_total_credits()),
            'Yes' if entry.is_balanced() else 'No',
            entry.created_at.strftime('%Y-%m-%d %H:%M:%S'),
            entry.created_by.username if entry.created_by else ''
        ])
    
    return response 