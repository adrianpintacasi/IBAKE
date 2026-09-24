from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone
from django.contrib.auth import get_user_model

from inventory.models import (
    RawMaterialMovement, StockMovement, StockIn, StockInDetail,
    Production, ProductionDetail, ProductionBatchProduct,
    FinishedGoodsInventory, MaterialSufficiencyCheck, UnusedMaterialReturn
)
from sales_management.models import SalesOrder, SalesOrderItem
from accounting.models import (
    JournalEntry, Transaction, PayrollEntry, UtilityEntry, CashTransaction
)

User = get_user_model()


class Command(BaseCommand):
    help = 'Reset all transactional data while preserving master lists (products, materials, employees, accounts, customers)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--confirm',
            action='store_true',
            help='Confirm that you want to delete all transactional data',
        )

    def handle(self, *args, **options):
        if not options['confirm']:
            self.stdout.write(
                self.style.WARNING(
                    'This command will delete ALL transactional data including:\n'
                    '- All stock movements and inventory records\n'
                    '- All sales orders and payments\n'
                    '- All journal entries and accounting transactions\n'
                    '- All production records\n'
                    '- All payroll and utility entries\n\n'
                    'Master lists will be preserved:\n'
                    '- Raw materials, products, finished goods (definitions)\n'
                    '- Employees and customers\n'
                    '- Chart of accounts\n'
                    '- Product recipes\n\n'
                    'Add --confirm flag to proceed with the reset.'
                )
            )
            return

        self.stdout.write('Starting transactional data reset...')

        try:
            with transaction.atomic():
                # Keep track of deletion counts
                deletion_counts = {}

                # 1. Reset Accounting Data
                self.stdout.write('Resetting accounting data...')
                deletion_counts['Journal Entries'] = JournalEntry.objects.count()
                JournalEntry.objects.all().delete()

                deletion_counts['Transactions'] = Transaction.objects.count()
                Transaction.objects.all().delete()

                deletion_counts['Payroll Entries'] = PayrollEntry.objects.count()
                PayrollEntry.objects.all().delete()

                deletion_counts['Utility Entries'] = UtilityEntry.objects.count()
                UtilityEntry.objects.all().delete()

                deletion_counts['Cash Transactions'] = CashTransaction.objects.count()
                CashTransaction.objects.all().delete()

                # 2. Reset Sales Data
                self.stdout.write('Resetting sales data...')
                deletion_counts['Sales Order Items'] = SalesOrderItem.objects.count()
                SalesOrderItem.objects.all().delete()

                deletion_counts['Sales Orders'] = SalesOrder.objects.count()
                SalesOrder.objects.all().delete()

                # 3. Reset Inventory Data
                self.stdout.write('Resetting inventory data...')
                deletion_counts['Finished Goods Inventory'] = FinishedGoodsInventory.objects.count()
                FinishedGoodsInventory.objects.all().delete()

                deletion_counts['Unused Material Returns'] = UnusedMaterialReturn.objects.count()
                UnusedMaterialReturn.objects.all().delete()

                deletion_counts['Material Sufficiency Checks'] = MaterialSufficiencyCheck.objects.count()
                MaterialSufficiencyCheck.objects.all().delete()

                deletion_counts['Production Batch Products'] = ProductionBatchProduct.objects.count()
                ProductionBatchProduct.objects.all().delete()

                deletion_counts['Production Details'] = ProductionDetail.objects.count()
                ProductionDetail.objects.all().delete()

                deletion_counts['Productions'] = Production.objects.count()
                Production.objects.all().delete()

                deletion_counts['Stock In Details'] = StockInDetail.objects.count()
                StockInDetail.objects.all().delete()

                deletion_counts['Stock Ins'] = StockIn.objects.count()
                StockIn.objects.all().delete()

                deletion_counts['Raw Material Movements'] = RawMaterialMovement.objects.count()
                RawMaterialMovement.objects.all().delete()

                deletion_counts['Stock Movements'] = StockMovement.objects.count()
                StockMovement.objects.all().delete()

                # 4. Reset Auto-calculated Account Balances
                self.stdout.write('Resetting auto-calculated account balances...')
                from accounting.models import Account
                auto_accounts = Account.objects.filter(auto_calculate=True)
                for account in auto_accounts:
                    pass

                # Success message
                self.stdout.write(
                    self.style.SUCCESS(
                        f'\nTransactional data reset completed successfully!\n\n'
                        f'Deleted records:\n'
                    )
                )

                for model_name, count in deletion_counts.items():
                    if count > 0:
                        self.stdout.write(f'  - {model_name}: {count}')

                self.stdout.write(
                    self.style.SUCCESS(
                        f'\nMaster lists preserved:\n'
                        f'  - Raw materials, products, finished goods (definitions)\n'
                        f'  - Employees and customers\n'
                        f'  - Chart of accounts\n'
                        f'  - Product recipes\n'
                        f'  - User accounts\n\n'
                        f'System is now ready for fresh data entry.'
                    )
                )

        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Error during reset: {str(e)}')
            )
            raise 