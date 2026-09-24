from django.core.management.base import BaseCommand
from django.utils import timezone
from inventory.models import FinishedGoodsInventory
from decimal import Decimal


class Command(BaseCommand):
    help = 'Check for expired finished goods and write them off with proper accounting'

    def add_arguments(self, parser):
        parser.add_argument(
            '--date',
            type=str,
            help='Check expiry as of specific date (YYYY-MM-DD). Default: today'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be expired without actually writing off'
        )

    def handle(self, *args, **options):
        # Parse date argument
        check_date = timezone.now().date()
        if options['date']:
            try:
                from datetime import datetime
                check_date = datetime.strptime(options['date'], '%Y-%m-%d').date()
            except ValueError:
                self.stdout.write(
                    self.style.ERROR('Invalid date format. Use YYYY-MM-DD')
                )
                return

        self.stdout.write(f"\n=== CHECKING EXPIRED GOODS AS OF {check_date} ===")

        # Get expired goods before processing
        expired_goods = FinishedGoodsInventory.objects.filter(
            expiry_date__lt=check_date,
            status='available',
            remaining_quantity__gt=0
        ).order_by('expiry_date')

        if not expired_goods.exists():
            self.stdout.write(
                self.style.SUCCESS('✅ No expired goods found!')
            )
            return

        # Show what would be expired
        self.stdout.write(f"\nFound {expired_goods.count()} expired batches:")
        
        total_quantity = Decimal('0')
        total_value = Decimal('0')
        
        for batch in expired_goods:
            from accounting.utils import calculate_product_cost
            cost_per_unit = calculate_product_cost(batch.product)
            batch_value = batch.remaining_quantity * cost_per_unit
            total_quantity += batch.remaining_quantity
            total_value += batch_value
            
            days_expired = (check_date - batch.expiry_date).days
            
            self.stdout.write(
                f"  • {batch.batch_number} - {batch.product.name}: "
                f"{batch.remaining_quantity} {batch.unit} "
                f"(₱{batch_value:.2f}) - Expired {days_expired} days ago"
            )

        self.stdout.write(f"\nTotal to write off: {total_quantity} units worth ₱{total_value:.2f}")

        if options['dry_run']:
            self.stdout.write(
                self.style.WARNING('\n🔍 DRY RUN - No changes made')
            )
            return

        # Actually process expired goods
        self.stdout.write(f"\nProcessing expired goods write-off...")
        
        expired_batches = FinishedGoodsInventory.check_and_expire_goods(check_date)
        
        if expired_batches:
            total_loss = sum(item['loss_value'] for item in expired_batches)
            self.stdout.write(
                self.style.SUCCESS(
                    f"✅ Successfully wrote off {len(expired_batches)} batches "
                    f"worth ₱{total_loss:.2f}"
                )
            )
            
            self.stdout.write("\nJournal Entry Created:")
            self.stdout.write(f"  Dr. Loss on Expired Goods: ₱{total_loss:.2f}")
            self.stdout.write(f"  Cr. Finished Goods Inventory: ₱{total_loss:.2f}")
            
        else:
            self.stdout.write(
                self.style.WARNING('No expired goods to process')
            )

        self.stdout.write(f"\n=== EXPIRED GOODS CHECK COMPLETED ===") 