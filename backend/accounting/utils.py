from decimal import Decimal
from django.db import models
from django.utils import timezone
from datetime import datetime, date, timedelta
from django.db.models import Sum, Q
from django.db.models import F
from core.datetime_utils import get_current_date, get_current_datetime

def calculate_accounts_receivable():
    """Calculate total accounts receivable from journal entry transactions"""
    from .models import Transaction, Account
    try:
        acct_rec_account = Account.objects.get(code='ACCT_REC')
        
        total_debits = Transaction.objects.filter(
            account=acct_rec_account
        ).aggregate(total=models.Sum('debit_amount'))['total'] or Decimal('0')
        
        total_credits = Transaction.objects.filter(
            account=acct_rec_account
        ).aggregate(total=models.Sum('credit_amount'))['total'] or Decimal('0')
        
        return total_debits - total_credits
        
    except Account.DoesNotExist:
        return Decimal('0')

def calculate_raw_materials_inventory():
    """Calculate raw materials inventory value"""
    try:
        from inventory.models import RawMaterial, RawMaterialMovement, StockInDetail
        total_value = Decimal('0')
        
        for material in RawMaterial.objects.all():
            available_stock = RawMaterialMovement.get_available_stock(material)
            if available_stock > 0:
                # Try to get latest purchase price from StockInDetail
                latest_stock_in = StockInDetail.objects.filter(
                    material=material
                ).order_by('-created_at').first()
                
                price_per_unit = latest_stock_in.unit_price if latest_stock_in else material.unit_cost
                
                # Convert available_stock from base units back to stock-in units
                # available_stock is in base units (e.g., grams)
                # price_per_unit is per stock-in unit (e.g., per kilogram)
                stock_in_units = material.from_base_unit(available_stock)
                total_value += stock_in_units * price_per_unit
        
        return total_value
    except ImportError:
        return Decimal('0')

def calculate_finished_goods_inventory():
    """Calculate finished goods inventory value"""
    try:
        from inventory.models import FinishedGoodsInventory, Product
        total_value = Decimal('0')
        
        # Get unique products to avoid double counting
        products_with_inventory = Product.objects.filter(
            finished_inventory__remaining_quantity__gt=0
        ).distinct()
        
        for product in products_with_inventory:
            available_stock = FinishedGoodsInventory.get_available_stock(product)
            if available_stock > 0:
                cost_per_unit = calculate_product_cost(product)
                total_value += Decimal(str(available_stock)) * cost_per_unit
        
        return total_value
    except ImportError:
        return Decimal('0')

def calculate_work_in_progress():
    """Calculate work in progress inventory value from in-progress productions"""
    try:
        from inventory.models import Production
        total_wip = Decimal('0')
        
        in_progress_productions = Production.objects.filter(status='in_progress')
        for production in in_progress_productions:
            wip_cost = calculate_production_cost(production)
            total_wip += wip_cost
        
        return total_wip
    except ImportError:
        return Decimal('0')

def calculate_production_cost(production):
    """Calculate the cost of materials used in a production"""
    try:
        from inventory.models import ProductionDetail, RawMaterialMovement, StockInDetail
        total_cost = Decimal('0')
        
        for detail in production.details.all():
            # Get the latest price for this material from StockInDetail
            latest_stock_in = StockInDetail.objects.filter(
                material=detail.raw_material
            ).order_by('-created_at').first()
            
            if latest_stock_in:
                # Stock-in price is per stock-in unit (e.g., per kg, per 250g package, etc.)
                # But production detail quantity_used is in production unit (e.g., grams)
                # We need to convert the quantity to match the pricing unit
                
                # If the units match, use directly
                if detail.unit == latest_stock_in.unit:
                    cost = detail.quantity_used * latest_stock_in.unit_price
                else:
                    # Extract the numeric value from stock-in unit for package-based conversions
                    stock_unit = latest_stock_in.unit
                    
                    # Handle different unit conversions
                    if detail.unit == 'g' and 'kg' in stock_unit:
                        # grams to kilograms (e.g., 239g with price per 1kg)
                        quantity_in_kg = detail.quantity_used / 1000
                        cost = quantity_in_kg * latest_stock_in.unit_price
                    elif detail.unit == 'ml' and 'L' in stock_unit:
                        # milliliters to liters (e.g., 179ml with price per 1L)
                        quantity_in_liters = detail.quantity_used / 1000
                        cost = quantity_in_liters * latest_stock_in.unit_price
                    elif detail.unit == 'pcs' and 'dozen' in stock_unit:
                        # pieces to dozens (e.g., 3pcs with price per 1dozen)
                        quantity_in_dozens = detail.quantity_used / 12
                        cost = quantity_in_dozens * latest_stock_in.unit_price
                    elif detail.unit == 'g' and 'g' in stock_unit:
                        # grams to package grams (e.g., 239g with price per 250g)
                        import re
                        package_size_match = re.search(r'(\d+)g', stock_unit)
                        if package_size_match:
                            package_size = int(package_size_match.group(1))
                            quantity_in_packages = detail.quantity_used / package_size
                            cost = quantity_in_packages * latest_stock_in.unit_price
                        else:
                            cost = detail.quantity_used * latest_stock_in.unit_price
                    elif detail.unit == 'ml' and 'ml' in stock_unit:
                        # milliliters to package milliliters (e.g., 4ml with price per 20ml)
                        import re
                        package_size_match = re.search(r'(\d+)ml', stock_unit)
                        if package_size_match:
                            package_size = int(package_size_match.group(1))
                            quantity_in_packages = detail.quantity_used / package_size
                            cost = quantity_in_packages * latest_stock_in.unit_price
                        else:
                            cost = detail.quantity_used * latest_stock_in.unit_price
                    else:
                        # Fallback: use the raw material's unit conversion factor
                        conversion_factor = detail.raw_material.unit_conversion_factor or 1
                        quantity_in_stock_units = detail.quantity_used / conversion_factor
                        cost = quantity_in_stock_units * latest_stock_in.unit_price
            else:
                # Use material's default unit cost
                cost = detail.quantity_used * detail.raw_material.unit_cost
            
            total_cost += cost
        
        return total_cost
    except ImportError:
        return Decimal('0')

def calculate_product_cost(product):
    """Calculate the cost of a product based on its recipe with proper unit conversion"""
    try:
        from inventory.models import ProductRecipe, RawMaterialMovement, StockInDetail
        import re
        
        recipe = ProductRecipe.objects.filter(product=product).first()
        if not recipe:
            return Decimal('10.00')  # Default cost if no recipe
        
        total_cost = Decimal('0')
        for detail in recipe.details.all():
            # Get latest purchase price for the material from StockInDetail
            latest_stock_in = StockInDetail.objects.filter(
                material=detail.material
            ).order_by('-created_at').first()
            
            if latest_stock_in:
                price_per_unit = latest_stock_in.unit_price
                recipe_quantity = detail.quantity
                recipe_unit = detail.unit
                stock_unit = latest_stock_in.unit
                
                # Convert recipe quantity to match stock-in unit for proper cost calculation
                if recipe_unit == stock_unit:
                    # Units match, use directly
                    cost = recipe_quantity * price_per_unit
                elif recipe_unit == 'g' and 'kg' in stock_unit:
                    # Convert grams to kilograms
                    quantity_in_kg = recipe_quantity / 1000
                    cost = quantity_in_kg * price_per_unit
                elif recipe_unit == 'ml' and 'L' in stock_unit:
                    # Convert milliliters to liters  
                    quantity_in_liters = recipe_quantity / 1000
                    cost = quantity_in_liters * price_per_unit
                elif recipe_unit == 'pcs' and 'dozen' in stock_unit:
                    # Convert pieces to dozens
                    quantity_in_dozens = recipe_quantity / 12
                    cost = quantity_in_dozens * price_per_unit
                elif recipe_unit == 'g' and 'g' in stock_unit:
                    # Handle package sizes like "250g", "400g"
                    package_size_match = re.search(r'(\d+)g', stock_unit)
                    if package_size_match:
                        package_size = int(package_size_match.group(1))
                        quantity_in_packages = recipe_quantity / package_size
                        cost = quantity_in_packages * price_per_unit
                    else:
                        cost = recipe_quantity * price_per_unit
                elif recipe_unit == 'ml' and 'ml' in stock_unit:
                    # Handle package sizes like "250ml", "20ml"
                    package_size_match = re.search(r'(\d+)ml', stock_unit)
                    if package_size_match:
                        package_size = int(package_size_match.group(1))
                        quantity_in_packages = recipe_quantity / package_size
                        cost = quantity_in_packages * price_per_unit
                    else:
                        cost = recipe_quantity * price_per_unit
                else:
                    # Fallback: use material's unit conversion factor if available
                    conversion_factor = getattr(detail.material, 'unit_conversion_factor', 1) or 1
                    quantity_in_stock_units = recipe_quantity / conversion_factor
                    cost = quantity_in_stock_units * price_per_unit
            else:
                # Use material's default unit cost
                cost = detail.quantity * detail.material.unit_cost
            
            total_cost += cost
        
        return total_cost
    except ImportError:
        return Decimal('10.00')

def calculate_sales_revenue():
    """Calculate total sales revenue from journal entry transactions"""
    from .models import Transaction, Account
    try:
        # Get sales revenue account
        sales_rev_account = Account.objects.get(code='SALES_REV')
        
        # Calculate total credits (revenue) minus debits (any adjustments)
        total_debits = Transaction.objects.filter(
            account=sales_rev_account
        ).aggregate(total=models.Sum('debit_amount'))['total'] or Decimal('0')
        
        total_credits = Transaction.objects.filter(
            account=sales_rev_account
        ).aggregate(total=models.Sum('credit_amount'))['total'] or Decimal('0')
        
        return total_credits - total_debits
        
    except Account.DoesNotExist:
        return Decimal('0')

def calculate_production_waste():
    """Calculate total production waste expense from journal entries"""
    from .models import Transaction, Account
    try:
        # Get production waste account
        waste_account = Account.objects.get(code='PROD_WASTE')
        
        # Calculate total debits (waste expenses) minus credits (any adjustments)
        total_debits = Transaction.objects.filter(
            account=waste_account
        ).aggregate(total=models.Sum('debit_amount'))['total'] or Decimal('0')
        
        total_credits = Transaction.objects.filter(
            account=waste_account
        ).aggregate(total=models.Sum('credit_amount'))['total'] or Decimal('0')
        
        return total_debits - total_credits
        
    except Account.DoesNotExist:
        return Decimal('0')

def calculate_expired_goods_loss():
    """Calculate total expired goods loss expense from journal entries"""
    from .models import Transaction, Account
    try:
        # Get expired goods loss account
        expired_account = Account.objects.get(code='EXP_GOODS')
        
        # Calculate total debits (loss expenses) minus credits (any adjustments)
        total_debits = Transaction.objects.filter(
            account=expired_account
        ).aggregate(total=models.Sum('debit_amount'))['total'] or Decimal('0')
        
        total_credits = Transaction.objects.filter(
            account=expired_account
        ).aggregate(total=models.Sum('credit_amount'))['total'] or Decimal('0')
        
        return total_debits - total_credits
        
    except Account.DoesNotExist:
        return Decimal('0')

def calculate_cost_of_goods_sold():
    """Calculate COGS from journal entry transactions"""
    from .models import Transaction, Account
    try:
        # Get COGS account
        cogs_account = Account.objects.get(code='COGS')
        
        # Calculate total debits (COGS expenses) minus credits (any adjustments)
        total_debits = Transaction.objects.filter(
            account=cogs_account
        ).aggregate(total=models.Sum('debit_amount'))['total'] or Decimal('0')
        
        total_credits = Transaction.objects.filter(
            account=cogs_account
        ).aggregate(total=models.Sum('credit_amount'))['total'] or Decimal('0')
        
        return total_debits - total_credits
        
    except Account.DoesNotExist:
        return Decimal('0')

def calculate_material_purchases():
    """Calculate total material purchases (cash outflows)"""
    try:
        from inventory.models import StockIn, StockInDetail
        
        # Calculate total from all stock in details for current year
        current_year = get_current_date().year
        total_purchases = Decimal('0')
        
        for stockin in StockIn.objects.filter(date__year=current_year):
            stockin_total = stockin.details.aggregate(
                total=Sum(F('quantity') * F('unit_price'))
            )['total'] or Decimal('0')
            total_purchases += stockin_total
        
        return total_purchases
    except ImportError:
        return Decimal('0')

def calculate_cash_balance():
    """Calculate cash balance from cash transactions and other operations"""
    from .models import Transaction, Account
    
    try:
        cash_account = Account.objects.get(code='CASH')
        return cash_account.get_current_balance()
    except Account.DoesNotExist:
        return Decimal('0')

def calculate_account_balance(account_code, as_of_date=None):
    """Calculate balance for a specific account as of a date"""
    from .models import Account, Transaction
    
    try:
        account = Account.objects.get(code=account_code)
        
        if account.auto_calculate:
            # Use automatic calculation
            if account_code == 'CASH':
                return calculate_cash_balance()
            elif account_code == 'ACCT_REC':
                return calculate_accounts_receivable()
            elif account_code == 'RAW_MAT':
                return calculate_raw_materials_inventory()
            elif account_code == 'FIN_GOODS':
                return calculate_finished_goods_inventory()
            elif account_code == 'WIP':
                return calculate_work_in_progress()
            elif account_code == 'SALES_REV':
                return calculate_sales_revenue()
            elif account_code == 'COGS':
                return calculate_cost_of_goods_sold()
            elif account_code == 'MAT_PURCH':
                return calculate_material_purchases()
            elif account_code == 'PROD_WASTE':
                return calculate_production_waste()
            elif account_code == 'EXP_GOODS':
                return calculate_expired_goods_loss()
            else:
                return account._calculate_auto_balance()
        else:
            return account.manual_balance
            
    except Account.DoesNotExist:
        return Decimal('0')

def generate_journal_entry_number():
    """Generate next journal entry number"""
    from .models import JournalEntry
    import re
    
    current_year = get_current_date().year
    
    # Get all existing entry numbers for current year and find the highest number
    existing_entries = JournalEntry.objects.filter(
        date__year=current_year,
        entry_number__startswith=f"{current_year}-"
    ).values_list('entry_number', flat=True)
    
    max_number = 0
    for entry_number in existing_entries:
        # Extract number from format "YYYY-NNNN"
        match = re.search(r'-(\d{4})$', entry_number)
        if match:
            number = int(match.group(1))
            max_number = max(max_number, number)
    
    next_number = max_number + 1
    return f"{current_year}-{next_number:04d}"

def create_journal_entry(description, transactions, reference_type=None, reference_id=None, entry_date=None, entry_number=None):
    """Create a journal entry with multiple transactions"""
    from .models import JournalEntry, Transaction, Account
    
    journal_entry = JournalEntry.objects.create(
        entry_number=entry_number or generate_journal_entry_number(),
        date=entry_date or get_current_date(),
        description=description,
        reference_type=reference_type,
        reference_id=reference_id
    )
    
    # Create transactions
    for trans_data in transactions:
        account = Account.objects.get(code=trans_data['account_code'])
        Transaction.objects.create(
            journal_entry=journal_entry,
            account=account,
            debit_amount=trans_data.get('debit', 0),
            credit_amount=trans_data.get('credit', 0),
            description=trans_data.get('description', '')
        )
    
    return journal_entry

def get_trial_balance_data(as_of_date=None, account_type=None):
    """Generate trial balance data using proper account balance calculations"""
    from .models import Account, Transaction
    from django.db import models
    from datetime import date, timedelta
    
    # If no specific date provided, use current date for real-time accuracy
    if as_of_date is None:
        as_of_date = get_current_date()
    
    trial_balance = []
    total_debits = Decimal('0')
    total_credits = Decimal('0')
    
    # Filter accounts by type if specified
    accounts_queryset = Account.objects.filter(is_active=True)
    if account_type:
        accounts_queryset = accounts_queryset.filter(account_type=account_type)
    
    for account in accounts_queryset.order_by('account_type', 'code'):
        # Only include accounts that have transactions or non-zero manual balances or auto-calculated balances
        has_transactions = Transaction.objects.filter(account=account).exists()
        has_manual_balance = not account.auto_calculate and account.manual_balance != 0
        
        # For auto-calculated accounts, get the calculated balance
        if account.auto_calculate:
            calculated_balance = calculate_account_balance(account.code, as_of_date)
            has_auto_balance = calculated_balance != 0
        else:
            has_auto_balance = False
            calculated_balance = Decimal('0')
        
        if has_transactions or has_manual_balance or has_auto_balance:
            if account.auto_calculate:
                # Use auto-calculated balance
                if account.normal_balance == 'DEBIT':
                    if calculated_balance >= 0:
                        debit_balance = calculated_balance
                        credit_balance = Decimal('0')
                    else:
                        debit_balance = Decimal('0')
                        credit_balance = abs(calculated_balance)
                else:  # CREDIT normal balance
                    if calculated_balance >= 0:
                        # For credit accounts, positive balance shows as credit
                        credit_balance = calculated_balance
                        debit_balance = Decimal('0')
                    else:
                        # For credit accounts, negative balance shows as debit
                        debit_balance = abs(calculated_balance)
                        credit_balance = Decimal('0')
            elif not account.auto_calculate and account.manual_balance != 0:
                # Use manual balance
                if account.normal_balance == 'DEBIT':
                    debit_balance = account.manual_balance
                    credit_balance = Decimal('0')
                else:
                    credit_balance = account.manual_balance
                    debit_balance = Decimal('0')
            else:
                # Use journal transaction balances for accounts without auto-calculation or manual balance
                trans_debits = Transaction.objects.filter(
                    account=account,
                    journal_entry__date__lte=as_of_date
                ).aggregate(total=models.Sum('debit_amount'))['total'] or Decimal('0')
                
                trans_credits = Transaction.objects.filter(
                    account=account,
                    journal_entry__date__lte=as_of_date
                ).aggregate(total=models.Sum('credit_amount'))['total'] or Decimal('0')
                
                net_balance = trans_debits - trans_credits
                
                if account.normal_balance == 'DEBIT':
                    if net_balance >= 0:
                        debit_balance = net_balance
                        credit_balance = Decimal('0')
                    else:
                        debit_balance = Decimal('0')
                        credit_balance = abs(net_balance)
                else:  # CREDIT normal balance
                    if net_balance <= 0:
                        credit_balance = abs(net_balance)
                        debit_balance = Decimal('0')
                    else:
                        credit_balance = Decimal('0')
                        debit_balance = net_balance
            
            trial_balance.append({
                'code': account.code,
                'name': account.name,
                'type': account.account_type,
                'balance': debit_balance if debit_balance > 0 else credit_balance,
                'debit_balance': debit_balance > 0,
                'debit_amount': debit_balance,
                'credit_amount': credit_balance
            })
            
            total_debits += debit_balance
            total_credits += credit_balance
    
    return trial_balance 