from django.core.management.base import BaseCommand
from accounting.models import Account


class Command(BaseCommand):
    help = 'Setup initial chart of accounts'

    def handle(self, *args, **options):
        self.stdout.write('Setting up Chart of Accounts...')

        # === ASSET ACCOUNTS ===
        Account.objects.get_or_create(
            code='CASH',
            defaults={
                'name': 'Cash',
                'account_type': 'ASSET',
                'normal_balance': 'DEBIT',
                'auto_calculate': True,
            }
        )

        Account.objects.get_or_create(
            code='ACCT_REC',
            defaults={
                'name': 'Accounts Receivable',
                'account_type': 'ASSET',
                'normal_balance': 'DEBIT',
                'auto_calculate': True,
            }
        )

        Account.objects.get_or_create(
            code='RAW_MAT',
            defaults={
                'name': 'Raw Materials Inventory',
                'account_type': 'ASSET',
                'normal_balance': 'DEBIT',
                'auto_calculate': True,
            }
        )

        Account.objects.get_or_create(
            code='WIP',
            defaults={
                'name': 'Work in Progress',
                'account_type': 'ASSET',
                'normal_balance': 'DEBIT',
                'auto_calculate': True,
            }
        )

        Account.objects.get_or_create(
            code='FIN_GOODS',
            defaults={
                'name': 'Finished Goods Inventory',
                'account_type': 'ASSET',
                'normal_balance': 'DEBIT',
                'auto_calculate': True,
            }
        )

        # === LIABILITY ACCOUNTS ===
        Account.objects.get_or_create(
            code='ACCT_PAY',
            defaults={
                'name': 'Accounts Payable',
                'account_type': 'LIABILITY',
                'normal_balance': 'CREDIT',
                'auto_calculate': True,
            }
        )

        # === REVENUE ACCOUNTS ===
        Account.objects.get_or_create(
            code='SALES_REV',
            defaults={
                'name': 'Sales Revenue',
                'account_type': 'REVENUE',
                'normal_balance': 'CREDIT',
                'auto_calculate': True,
            }
        )

        # === EXPENSE ACCOUNTS ===
        Account.objects.get_or_create(
            code='COGS',
            defaults={
                'name': 'Cost of Goods Sold',
                'account_type': 'EXPENSE',
                'normal_balance': 'DEBIT',
                'auto_calculate': True,
            }
        )

        Account.objects.get_or_create(
            code='MAT_PURCH',
            defaults={
                'name': 'Material Purchases',
                'account_type': 'EXPENSE',
                'normal_balance': 'DEBIT',
                'auto_calculate': False,  # Disabled to avoid double-counting
            }
        )

        Account.objects.get_or_create(
            code='PROD_WASTE',
            defaults={
                'name': 'Production Waste',
                'account_type': 'EXPENSE',
                'normal_balance': 'DEBIT',
                'auto_calculate': True,
            }
        )

        Account.objects.get_or_create(
            code='EXP_GOODS',
            defaults={
                'name': 'Loss on Expired Goods',
                'account_type': 'EXPENSE',
                'normal_balance': 'DEBIT',
                'auto_calculate': True,
            }
        )

        self.stdout.write(
            self.style.SUCCESS('✅ Chart of Accounts setup completed successfully!')
        ) 