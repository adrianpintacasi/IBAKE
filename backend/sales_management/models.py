from django.db import models, transaction
from django.core.exceptions import ValidationError
from inventory.models import Product
from employee.models import Employee
from django.utils import timezone
from core.datetime_utils import get_current_date, get_current_datetime

class BaseModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)
    class Meta:
        abstract = True

class SalesOrder(BaseModel):
    STATUS_CHOICES = [
        ('New', 'New'),
        ('Open', 'Open'),
        ('Paid', 'Paid'),
    ]
    sales_order_id = models.AutoField(primary_key=True)
    order_date = models.DateTimeField(auto_now_add=True)
    customer_name = models.CharField(max_length=255)
    customer_address = models.TextField(blank=True, null=True)
    employee = models.ForeignKey(Employee, on_delete=models.SET_NULL, null=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='New')
    total_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    amount_paid = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    def __str__(self):
        return f"Sales Order #{self.sales_order_id}"

    def calculate_total(self):
        total = self.salesorderitem_set.aggregate(
            total=models.Sum('subtotal')
        )['total'] or 0
        if self.total_amount != total:
            self.total_amount = total
            self.save(update_fields=['total_amount'])
        return total

    @property
    def balance(self):
        return self.total_amount - self.amount_paid
    
    def update_status(self):
        """Update status based on payment amount"""
        if self.amount_paid <= 0:
            self.status = 'New'
        elif self.amount_paid >= self.total_amount:
            self.status = 'Paid'
        else:
            self.status = 'Open'
    
    def add_payment(self, amount):
        """Add a payment and update status with proper journal entry creation"""
        from decimal import Decimal
        
        if amount <= 0:
            raise ValueError("Payment amount must be greater than zero")
        
        # Store old balance for journal entry calculation
        old_balance = self.balance
        
        if old_balance <= 0:
            raise ValueError("No outstanding balance to pay")
        
        # Use atomic transaction to ensure payment and journal entry are both created or both fail
        with transaction.atomic():
            # Update payment amount and status
            self.amount_paid += amount
            self.update_status()
            self.save()
            
            # Create automatic journal entry for payment
            # Calculate the actual A/R amount being paid (use old_balance, not self.balance)
            ar_payment_amount = min(amount, old_balance)
            
            from accounting.utils import create_journal_entry
            
            journal_entry = create_journal_entry(
                    description=f'Sales Order #{self.sales_order_id} - Payment Collection',
                    transactions=[
                        {
                            'account_code': 'CASH',
                            'debit': ar_payment_amount,
                            'credit': Decimal('0'),
                            'description': f'Payment received for Sales Order #{self.sales_order_id}'
                        },
                        {
                            'account_code': 'ACCT_REC',
                            'debit': Decimal('0'),
                            'credit': ar_payment_amount,
                            'description': f'A/R collection for Sales Order #{self.sales_order_id}'
                    }
                ],
                reference_type='sales_payment',
                reference_id=self.sales_order_id,
                entry_date=get_current_date()
            )
            
            return self.balance, journal_entry
    
    def create_missing_journal_entries(self):
        """Create journal entries for sales orders that don't have them (retroactive fix)"""
        from decimal import Decimal
        from accounting.models import JournalEntry
        from accounting.utils import create_journal_entry, calculate_product_cost
        
        # Check if journal entries already exist
        existing_entries = JournalEntry.objects.filter(
            reference_type='sales_order',
            reference_id=self.sales_order_id
        ).count()
        
        if existing_entries > 0:
            return f"Sales Order #{self.sales_order_id} already has {existing_entries} journal entries"
        
        if self.total_amount <= 0:
            return f"Sales Order #{self.sales_order_id} has no amount to record"
        
        with transaction.atomic():
            # Calculate COGS for this order
            cogs_total = Decimal('0')
            for item in self.salesorderitem_set.all():
                product_cost = calculate_product_cost(item.product)
                cogs_total += Decimal(str(item.quantity)) * product_cost
            
            # Create revenue journal entry
            revenue_transactions = []
            amount_receivable = self.total_amount - self.amount_paid
            
            if self.amount_paid > 0:
                # Cash received
                revenue_transactions.append({
                    'account_code': 'CASH',
                    'debit': Decimal(str(self.amount_paid)),
                    'credit': Decimal('0'),
                    'description': f'Cash received - Sales Order #{self.sales_order_id}'
                })
            
            if amount_receivable > 0:
                # Amount still owed
                revenue_transactions.append({
                    'account_code': 'ACCT_REC',
                    'debit': Decimal(str(amount_receivable)),
                    'credit': Decimal('0'),
                    'description': f'Amount receivable - Sales Order #{self.sales_order_id}'
                })
            
            # Sales revenue (credit)
            revenue_transactions.append({
                'account_code': 'SALES_REV',
                'debit': Decimal('0'),
                'credit': Decimal(str(self.total_amount)),
                'description': f'Sales revenue - Sales Order #{self.sales_order_id}'
            })
            
            # Create revenue journal entry
            revenue_entry = create_journal_entry(
                description=f"Sales Order #{self.sales_order_id} - Revenue Recognition (Retroactive)",
                transactions=revenue_transactions,
                reference_type='sales_order',
                reference_id=self.sales_order_id,
                entry_date=self.order_date.date()
            )
            
            # Create COGS journal entry
            cogs_entry = None
            if cogs_total > 0:
                cogs_entry = create_journal_entry(
                    description=f"Sales Order #{self.sales_order_id} - Cost of Goods Sold (Retroactive)",
                    transactions=[
                        {
                            'account_code': 'COGS',
                            'debit': cogs_total,
                            'credit': Decimal('0'),
                            'description': f'COGS - Sales Order #{self.sales_order_id}'
                        },
                        {
                            'account_code': 'FIN_GOODS',
                            'debit': Decimal('0'),
                            'credit': cogs_total,
                            'description': f'Finished goods sold - Sales Order #{self.sales_order_id}'
                        }
                    ],
                    reference_type='sales_order',
                    reference_id=self.sales_order_id,
                    entry_date=self.order_date.date()
                )
        
            return f"Created journal entries: {revenue_entry.entry_number}" + (f" and {cogs_entry.entry_number}" if cogs_entry else "")
    
    def save(self, *args, **kwargs):
        # Auto-update status when saving
        self.update_status()
        super().save(*args, **kwargs)

class SalesOrderItem(BaseModel):
    sales_order_item_id = models.AutoField(primary_key=True)
    sales_order = models.ForeignKey(SalesOrder, on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField()
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)
    discount = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    subtotal = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    def __str__(self):
        return f"{self.quantity} x {self.product.name}"

    def calculate_subtotal(self):
        self.subtotal = self.quantity * self.unit_price * (1 - self.discount/100)
        return self.subtotal

    def save(self, *args, **kwargs):
        is_new = self._state.adding
        if not self.subtotal or self.subtotal == 0:
            self.calculate_subtotal()
        super().save(*args, **kwargs)
        if self.sales_order_id:
            total = self.sales_order.salesorderitem_set.aggregate(
                total=models.Sum('subtotal')
            )['total'] or 0
            self.sales_order.total_amount = total
            self.sales_order.save(update_fields=['total_amount'])
