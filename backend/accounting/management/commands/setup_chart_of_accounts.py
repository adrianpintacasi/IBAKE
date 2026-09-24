from django.core.management.base import BaseCommand
from django.db import transaction
from accounting.models import Account

class Command(BaseCommand):
    help = 'Setup initial chart of accounts for iBAKE Cakes & Pastries'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('Setting up Chart of Accounts for iBAKE Cakes & Pastries...'))
        
        accounts_data = [
            # ASSETS
            {
                'code': 'CASH',
                'name': 'Cash',
                'account_type': 'ASSET',
                'normal_balance': 'DEBIT',
                'auto_calculate': True,
                'manual_balance': 0
            },
            {
                'code': 'ACCT_REC',
                'name': 'Accounts Receivable',
                'account_type': 'ASSET',
                'normal_balance': 'DEBIT',
                'auto_calculate': True,
                'manual_balance': 0
            },
            {
                'code': 'RAW_MAT',
                'name': 'Raw Materials Inventory',
                'account_type': 'ASSET',
                'normal_balance': 'DEBIT',
                'auto_calculate': True,
                'manual_balance': 0
            },
            {
                'code': 'WIP',
                'name': 'Work in Progress',
                'account_type': 'ASSET',
                'normal_balance': 'DEBIT',
                'auto_calculate': True,
                'manual_balance': 0
            },
            {
                'code': 'FIN_GOODS',
                'name': 'Finished Goods Inventory',
                'account_type': 'ASSET',
                'normal_balance': 'DEBIT',
                'auto_calculate': True,
                'manual_balance': 0
            },
            {
                'code': 'EQUIPMENT',
                'name': 'Equipment',
                'account_type': 'ASSET',
                'normal_balance': 'DEBIT',
                'auto_calculate': False,
                'manual_balance': 0
            },
            
            # LIABILITIES
            {
                'code': 'ACCT_PAY',
                'name': 'Accounts Payable',
                'account_type': 'LIABILITY',
                'normal_balance': 'CREDIT',
                'auto_calculate': False,
                'manual_balance': 0
            },
            
            # EQUITY
            {
                'code': 'OWNER_EQ',
                'name': "Owner's Equity",
                'account_type': 'EQUITY',
                'normal_balance': 'CREDIT',
                'auto_calculate': False,
                'manual_balance': 0
            },
            {
                'code': 'RET_EARN',
                'name': 'Retained Earnings',
                'account_type': 'EQUITY',
                'normal_balance': 'CREDIT',
                'auto_calculate': True,
                'manual_balance': 0
            },
            
            # REVENUE
            {
                'code': 'SALES_REV',
                'name': 'Sales Revenue',
                'account_type': 'REVENUE',
                'normal_balance': 'CREDIT',
                'auto_calculate': True,
                'manual_balance': 0
            },
            
            # EXPENSES
            {
                'code': 'COGS',
                'name': 'Cost of Goods Sold',
                'account_type': 'EXPENSE',
                'normal_balance': 'DEBIT',
                'auto_calculate': True,
                'manual_balance': 0
            },
            {
                'code': 'PAYROLL',
                'name': 'Payroll Expense',
                'account_type': 'EXPENSE',
                'normal_balance': 'DEBIT',
                'auto_calculate': False,
                'manual_balance': 0
            },
            {
                'code': 'UTILITIES',
                'name': 'Utilities Expense',
                'account_type': 'EXPENSE',
                'normal_balance': 'DEBIT',
                'auto_calculate': False,
                'manual_balance': 0
            },
                        {                'code': 'MAT_PURCH',                'name': 'Material Purchases',                'account_type': 'EXPENSE',                'normal_balance': 'DEBIT',                'auto_calculate': False,                'manual_balance': 0            },
            {
                'code': 'OTHER_INC',
                'name': 'Other Income',
                'account_type': 'REVENUE',
                'normal_balance': 'CREDIT',
                'auto_calculate': False,
                'manual_balance': 0
            },
            {
                'code': 'OTHER_EXP',
                'name': 'Other Expense',
                'account_type': 'EXPENSE',
                'normal_balance': 'DEBIT',
                'auto_calculate': False,
                'manual_balance': 0
            },
            {
                'code': 'PROD_WASTE',
                'name': 'Production Waste Expense',
                'account_type': 'EXPENSE',
                'normal_balance': 'DEBIT',
                'auto_calculate': True,
                'manual_balance': 0
            },
        ]
        
        with transaction.atomic():
            created_count = 0
            updated_count = 0
            
            for account_data in accounts_data:
                account, created = Account.objects.get_or_create(
                    code=account_data['code'],
                    defaults=account_data
                )
                
                if created:
                    created_count += 1
                    self.stdout.write(
                        self.style.SUCCESS(f'✅ Created account: {account.code} - {account.name}')
                    )
                else:
                    # Update existing account if needed
                    for field, value in account_data.items():
                        if hasattr(account, field):
                            setattr(account, field, value)
                    account.save()
                    updated_count += 1
                    self.stdout.write(
                        self.style.WARNING(f'🔄 Updated account: {account.code} - {account.name}')
                    )
        
        self.stdout.write(
            self.style.SUCCESS(
                f'\n🎉 Chart of Accounts setup complete!\n'
                f'Created: {created_count} accounts\n'
                f'Updated: {updated_count} accounts\n'
                f'Total: {len(accounts_data)} accounts configured'
            )
        ) 