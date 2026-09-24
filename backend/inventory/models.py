from django.db import models
from django.core.validators import MinValueValidator
from decimal import Decimal
from django.utils import timezone
from datetime import date
from core.datetime_utils import get_current_date, get_current_datetime

class RawMaterial(models.Model):
    CATEGORY_CHOICES = [
        ('ingredients', 'Ingredients'),
        ('packaging', 'Packaging'),
        ('supplies', 'Supplies'),
        ('beverages', 'Beverages'),
        ('dairy', 'Dairy'),
        ('produce', 'Produce'),
        ('spices', 'Spices'),
        ('other', 'Other'),
    ]

    code = models.CharField(max_length=20, unique=True)
    name = models.CharField(max_length=100)
    brand = models.CharField(max_length=100, blank=True)
    description = models.TextField(blank=True)
    category = models.CharField(max_length=50, choices=CATEGORY_CHOICES)
    unit = models.CharField(max_length=20)
    minimum_stock = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    unit_cost = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    base_unit = models.CharField(max_length=10, default='g', help_text='Base unit for inventory (e.g., g, ml, pcs)')
    unit_conversion_factor = models.DecimalField(max_digits=10, decimal_places=2, default=1, help_text='How many base units in one stock-in unit (e.g., 1000 for 1kg if base unit is g)')

    class Meta:
        verbose_name = 'Raw Material'
        verbose_name_plural = 'Raw Materials'
        ordering = ['code']

    def __str__(self):
        return f"{self.code} - {self.name}"

    def save(self, *args, **kwargs):
        if not self.code:
            # Get the last code used
            last_material = RawMaterial.objects.order_by('-code').first()
            if last_material and last_material.code.startswith('RM'):
                try:
                    last_number = int(last_material.code[2:])
                    new_number = last_number + 1
                except ValueError:
                    new_number = 1
            else:
                new_number = 1
            self.code = f'RM{new_number:04d}'
        super().save(*args, **kwargs)

    def to_base_unit(self, quantity):
        """Convert a quantity in the stock-in unit to the base unit."""
        return Decimal(quantity) * self.unit_conversion_factor

    def from_base_unit(self, quantity):
        """Convert a quantity in the base unit to the stock-in unit."""
        return Decimal(quantity) / self.unit_conversion_factor

class FinishedGood(models.Model):
    code = models.CharField(max_length=20, unique=True)
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    category = models.CharField(max_length=50)
    unit = models.CharField(max_length=20)
    minimum_stock = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    unit_price = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Finished Good'
        verbose_name_plural = 'Finished Goods'
        ordering = ['code']

    def __str__(self):
        return f"{self.code} - {self.name}"

class ProductRecipe(models.Model):
    employee = models.ForeignKey('employee.Employee', on_delete=models.PROTECT, null=True, blank=True)
    recipe_number = models.CharField(max_length=20, unique=True, blank=True, null=True)
    product = models.ForeignKey('Product', on_delete=models.CASCADE, related_name='recipes')
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Product Recipe'
        verbose_name_plural = 'Product Recipes'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.recipe_number} - {self.product.name}"

    def save(self, *args, **kwargs):
        if not self.recipe_number:
            # Generate recipe number
            last_recipe = ProductRecipe.objects.order_by('-recipe_number').first()
            if last_recipe and last_recipe.recipe_number.startswith('REC'):
                try:
                    last_number = int(last_recipe.recipe_number[3:])
                    new_number = last_number + 1
                except ValueError:
                    new_number = 1
            else:
                new_number = 1
            self.recipe_number = f'REC{new_number:06d}'
        super().save(*args, **kwargs)

class ProductRecipeDetail(models.Model):
    recipe = models.ForeignKey(ProductRecipe, on_delete=models.CASCADE, related_name='details')
    material = models.ForeignKey(RawMaterial, on_delete=models.PROTECT)
    quantity = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(Decimal('0.01'))])
    unit = models.CharField(max_length=20)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Recipe Detail'
        verbose_name_plural = 'Recipe Details'
        ordering = ['recipe', 'material']
        unique_together = ['recipe', 'material']

    def __str__(self):
        return f"{self.recipe.recipe_number} - {self.material.name}"

    def save(self, *args, **kwargs):
        # If unit is not provided, use the material's default unit
        if not self.unit and self.material:
            self.unit = self.material.unit
        super().save(*args, **kwargs)

class Production(models.Model):
    STATUS_CHOICES = [
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    ]

    production_number = models.CharField(max_length=50, unique=True, blank=True)
    date_started = models.DateField(null=True, blank=True)
    date_finished = models.DateField(null=True, blank=True)
    product = models.ForeignKey('Product', on_delete=models.CASCADE, null=True, blank=True)  # Nullable for mixed batches
    quantity_produced = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    unit = models.CharField(max_length=50, default='pcs')
    employee = models.ForeignKey('employee.Employee', on_delete=models.SET_NULL, null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='in_progress')
    notes = models.TextField(blank=True)
    wastage_notes = models.TextField(blank=True, help_text="Notes about material wastage during cancellation")
    material_sufficiency_checked = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Production'
        verbose_name_plural = 'Productions'
        ordering = ['-date_started', '-production_number']

    def __str__(self):
        if self.product:
            return f"{self.production_number} - {self.product.name}"
        return f"{self.production_number} - Mixed Batch"

    def save(self, *args, **kwargs):
        if not self.production_number:
            last_prod = Production.objects.order_by('-production_number').first()
            if last_prod and last_prod.production_number.startswith('PROD'):
                try:
                    last_number = int(last_prod.production_number[4:])
                    new_number = last_number + 1
                except ValueError:
                    new_number = 1
            else:
                new_number = 1
            self.production_number = f'PROD{new_number:06d}'
        super().save(*args, **kwargs)

    def can_edit(self):
        return self.status not in ['completed', 'cancelled']

    def get_all_products(self):
        """Get all products in this production (single or mixed batch)"""
        if self.product:
            return [{'product': self.product, 'quantity': self.quantity_produced}]
        else:
            return [{'product': bp.product, 'quantity': bp.quantity} for bp in self.batch_products.all()]

    def check_material_sufficiency(self):
        """
        Check if there are sufficient materials for all products in this production.
        Returns dict with overall status and individual checks.
        """
        all_products = self.get_all_products()
        if not all_products:
            return {'sufficient': False, 'checks': [], 'message': 'No products defined'}

        checks = []
        overall_sufficient = True

        # Clear existing checks
        self.sufficiency_checks.all().delete()

        # Aggregate material requirements across all products
        material_requirements = {}  
        
        for product_info in all_products:
            product = product_info['product']
            quantity = product_info['quantity']
            
            # Get active recipe for this product
            recipe = product.recipes.filter(is_active=True).first()
            if not recipe:
                overall_sufficient = False
                continue

            # Aggregate each ingredient in the recipe
            for recipe_detail in recipe.details.all():
                material_id = recipe_detail.material.id
                required_qty = recipe_detail.quantity * quantity
                
                if material_id not in material_requirements:
                    material_requirements[material_id] = {
                        'material': recipe_detail.material,
                        'required_qty': Decimal('0'),
                        'unit': recipe_detail.unit
                    }
                
                material_requirements[material_id]['required_qty'] += required_qty

        #sufficiency check records for aggregated requirements
        for material_id, req_data in material_requirements.items():
            material = req_data['material']
            required_qty = req_data['required_qty']
            unit = req_data['unit']
            
            available_qty = RawMaterialMovement.get_available_stock(material)
            is_sufficient = available_qty >= required_qty
            
            if not is_sufficient:
                overall_sufficient = False

            # Create sufficiency check record (only one per material now)
            check = MaterialSufficiencyCheck.objects.create(
                production=self,
                raw_material=material,
                required_quantity=required_qty,
                available_quantity=available_qty,
                is_sufficient=is_sufficient,
                unit=unit
            )
            checks.append(check)

        self.material_sufficiency_checked = True
        if overall_sufficient:
            self.status = 'in_progress'  
        else:
            self.status = 'cancelled'  
        self.save(update_fields=['material_sufficiency_checked', 'status'])

        return {
            'sufficient': overall_sufficient,
            'checks': checks,
            'message': 'Materials sufficient' if overall_sufficient else 'Some materials are insufficient'
        }

    def get_standardized_unit_cost(self, raw_material, required_unit):
        """
        Get unit cost standardized to the required unit.
        This ensures we're comparing apples to apples when calculating costs.
        """
        # Get latest price for this material
        latest_stock_in = StockInDetail.objects.filter(
            material=raw_material
        ).order_by('-created_at').first()
        
        if latest_stock_in:
            stock_in_unit_cost = latest_stock_in.unit_price
            stock_in_unit = latest_stock_in.unit
            
            # If both units are the same, return cost as-is
            if stock_in_unit == required_unit:
                return stock_in_unit_cost
            
            # Convert stock-in cost to base unit cost first
            if stock_in_unit == raw_material.unit: 
              
                base_unit_cost = stock_in_unit_cost / raw_material.unit_conversion_factor
            else:
                # Assume stock-in unit is already in base units or use as-is
                base_unit_cost = stock_in_unit_cost
            
            # Convert base unit cost to required unit cost
            if required_unit == raw_material.base_unit:
                return base_unit_cost
            elif required_unit == raw_material.unit:
                return base_unit_cost * raw_material.unit_conversion_factor
            else:
                return base_unit_cost
        else:
            # Fallback to material's default unit cost
            if required_unit == raw_material.unit:
                return raw_material.unit_cost
            elif required_unit == raw_material.base_unit:
                return raw_material.unit_cost / raw_material.unit_conversion_factor
            else:
                return raw_material.unit_cost / raw_material.unit_conversion_factor

    def start_production(self):
        """Start production by consuming materials and creating production details"""
        from django.db import transaction
        
        if self.status != 'in_progress':
            return False, "Production must be in progress to start"

        # Check if materials have been consumed already
        if self.details.exists():
            return False, "Production has already been started"

        all_products = self.get_all_products()
        
        try:
            with transaction.atomic():
                total_material_cost = Decimal('0')
                
                for product_info in all_products:
                    product = product_info['product']
                    quantity = product_info['quantity']
                    

                    recipe = product.recipes.filter(is_active=True).first()
                    if not recipe:
                        return False, f"No active recipe found for {product.name}"

                   
                    for recipe_detail in recipe.details.all():
                        required_quantity = recipe_detail.quantity * quantity
                        
                       
                        unit_cost = self.get_standardized_unit_cost(recipe_detail.material, recipe_detail.unit)
                        material_cost = required_quantity * unit_cost
                        total_material_cost += material_cost
                        
                        
                        success = self._consume_material_fefo(
                            recipe_detail.material,
                            required_quantity,
                            recipe_detail.unit
                        )
                        
                        if not success:
                            # Transaction will automatically cancel
                            return False, f"Failed to consume {recipe_detail.material.name}"


                self.date_started = get_current_date()
                self.save(update_fields=['date_started'])
                
                if total_material_cost > 0:
                    try:
                        from accounting.utils import create_journal_entry
                        
                        create_journal_entry(
                            description=f"Production #{self.production_number} - Materials transferred to WIP",
                            transactions=[
                                {
                                    'account_code': 'WIP',
                                    'debit': total_material_cost,
                                    'credit': Decimal('0'),
                                    'description': f'Materials moved to Work in Process - Production #{self.production_number}'
                                },
                                {
                                    'account_code': 'RAW_MAT',
                                    'debit': Decimal('0'),
                                    'credit': total_material_cost,
                                    'description': f'Raw materials consumed in production #{self.production_number}'
                                }
                            ],
                            reference_type='production_start',
                            reference_id=self.id,
                            entry_date=None  
                        )
                    except Exception as e:
                        print(f"Production start journal entry error: {e}")
                        import traceback
                        traceback.print_exc()
                     
                
                return True, "Production materials consumed successfully"
                
        except Exception as e:
            print(f"Error in start_production: {e}")
            import traceback
            traceback.print_exc()
            return False, f"Production start failed: {str(e)}"

    def _consume_material_fefo(self, raw_material, quantity, unit):
        """Consume raw material using FEFO method based on expiry dates"""
        try:
            # SIMPLIFIED FEFO LOGIC
            

            available_movements = RawMaterialMovement.objects.filter(
                raw_material=raw_material,
                movement_type__in=['IN', 'ADJ'],
                remaining_quantity__gt=0
            ).order_by('date')
            
            if not available_movements.exists():
                return False
            
            # Convert required quantity to base units 
            if unit == raw_material.base_unit:
                required_base_quantity = quantity
            else:
                # Convert to base units 
                required_base_quantity = raw_material.to_base_unit(quantity)
            
           
            total_available = sum(movement.remaining_quantity for movement in available_movements)
            
            if total_available < required_base_quantity:
                return False
            
            # Separate movements by expiry date for FEFO
            movements_with_expiry = []
            movements_without_expiry = []
            
            for movement in available_movements:
                
                stock_detail = None
                if 'StockIn #' in movement.reference:
                    try:
                        stockin_id = movement.reference.split('#')[1]
                        stock_detail = StockInDetail.objects.filter(
                            stock_in_id=stockin_id,
                            material=raw_material
                        ).first()
                    except (IndexError, ValueError):
                        pass
                
                if stock_detail and stock_detail.expiry_date:
                    movements_with_expiry.append((movement, stock_detail.expiry_date))
                else:
                    movements_without_expiry.append((movement, None))
            
            # Sort movements with expiry dates by expiry date (FEFO)
            movements_with_expiry.sort(key=lambda x: x[1])
            
           
            all_movements = movements_with_expiry + movements_without_expiry
            
            # Consume materials from movements
            remaining_to_consume = required_base_quantity
            consumed_batches = []
            
            for movement_data in all_movements:
                if remaining_to_consume <= 0:
                    break
                    
                movement = movement_data[0]
                expiry_date = movement_data[1]
                
                if movement.remaining_quantity >= remaining_to_consume:
                    
                    movement.remaining_quantity -= remaining_to_consume
                    movement.save()
                    
                   
                    if unit == raw_material.base_unit:
                        consumed_in_recipe_unit = remaining_to_consume
                    else:
                        consumed_in_recipe_unit = raw_material.from_base_unit(remaining_to_consume)
                    
                    consumed_batches.append({
                        'movement': movement,
                        'quantity_consumed': consumed_in_recipe_unit,
                        'expiry_date': expiry_date
                    })
                    
                    # Create production detail record
                    notes_suffix = f'from batch expiring {expiry_date}' if expiry_date else 'from batch (no expiry date)'
                    ProductionDetail.objects.create(
                        production=self,
                        raw_material=raw_material,
                        quantity_used=consumed_in_recipe_unit,
                        unit=unit,
                        source_batch=None,
                        notes=f'FEFO consumption {notes_suffix}'
                    )
                    
                    remaining_to_consume = 0
                else:
                    # Consume entire movement
                    consumed_base_quantity = movement.remaining_quantity
                    
                   
                    if unit == raw_material.base_unit:
                        consumed_in_recipe_unit = consumed_base_quantity
                    else:
                        consumed_in_recipe_unit = raw_material.from_base_unit(consumed_base_quantity)
                    
                    consumed_batches.append({
                        'movement': movement,
                        'quantity_consumed': consumed_in_recipe_unit,
                        'expiry_date': expiry_date
                    })
                    
                    # Create production detail record
                    notes_suffix = f'from batch expiring {expiry_date}' if expiry_date else 'from batch (no expiry date)'
                    ProductionDetail.objects.create(
                        production=self,
                        raw_material=raw_material,
                        quantity_used=consumed_in_recipe_unit,
                        unit=unit,
                        source_batch=None,
                        notes=f'FEFO consumption {notes_suffix}'
                    )
                    
                    remaining_to_consume -= consumed_base_quantity
                    movement.remaining_quantity = 0
                    movement.save()

            # Create OUT movement record for the total consumption
            total_consumed_base = required_base_quantity - remaining_to_consume
            if total_consumed_base > 0:
                RawMaterialMovement.objects.create(
                    movement_type='OUT',
                    raw_material=raw_material,
                    quantity=total_consumed_base,  # Always store in base units
                    unit=unit,  # But record the recipe unit for reference
                    reference=f'Production #{self.production_number or self.id}',
                    notes=f'Used in production of {self.get_products_display()} (FEFO)'
                )

            # Return success if we consumed everything
            if remaining_to_consume <= 0:
                return True
            else:
                return False

        except Exception as e:
            print(f"Error in FEFO method for {raw_material.name}: {e}")
            import traceback
            traceback.print_exc()
            return False

    def get_products_display(self):
        """Get display string for products in this production"""
        products = self.get_all_products()
        if len(products) == 1:
            return products[0]['product'].name
        return f"Mixed batch ({len(products)} products)"

    def complete_production(self):
        """Complete production and add to finished goods inventory"""
        if self.status != 'in_progress':
            return False, "Production must be in progress to complete"

        all_products = self.get_all_products()
        total_production_cost = Decimal('0')
        
        for product_info in all_products:
            product = product_info['product']
            quantity = product_info['quantity']
            
            # Add to finished goods inventory
            FinishedGoodsInventory.objects.create(
                product=product,
                production=self,
                quantity=quantity,
                production_date=get_current_date(),
                unit=self.unit
            )
            
            try:
                from accounting.utils import calculate_product_cost
                product_cost = calculate_product_cost(product)
                total_production_cost += quantity * product_cost
            except ImportError:
                pass

        self.status = 'completed'
        self.date_finished = get_current_date()
        self.save(update_fields=['status', 'date_finished'])
        
        if total_production_cost > 0:
            try:
                from accounting.utils import create_journal_entry
                
                create_journal_entry(
                    description=f"Production #{self.production_number} - Production Completion",
                    transactions=[
                        {
                            'account_code': 'FIN_GOODS',
                            'debit': total_production_cost,
                            'credit': Decimal('0'),
                            'description': f'Finished goods produced - Production #{self.production_number}'
                        },
                        {
                            'account_code': 'WIP',
                            'debit': Decimal('0'),
                            'credit': total_production_cost,
                            'description': f'Work in Process transferred to finished goods - Production #{self.production_number}'
                        }
                    ],
                    reference_type='production_complete',
                    reference_id=self.id,
                    entry_date=None  # Use current date for real-time accuracy
                )
            except Exception as e:
                print(f"Production journal entry error: {e}")
                import traceback
                traceback.print_exc()
        
        return True, "Production completed and added to finished goods inventory"

    def cancel_production(self, unused_materials_data=None, employee=None, cancellation_reason='', return_notes=''):
        """
        Cancel production and optionally return unused materials to inventory
        unused_materials_data should be a list of dicts: [{'material_id': x, 'quantity_returned': y, 'notes': 'reason'}]
        """
        if self.status in ['completed', 'cancelled']:
            return False, "Cannot cancel completed or already cancelled production"

        # Save cancellation reason to wastage_notes field
        if cancellation_reason:
            self.wastage_notes = cancellation_reason

        # Handle unused material returns
        if unused_materials_data:
            # If no employee provided, try to get the first available employee or create a default one
            if not employee:
                from employee.models import Employee
                employee = Employee.objects.filter(is_active=True).first()
                if not employee:
                    # Create a default system employee if none exists
                    employee = Employee.objects.create(
                        first_name='System',
                        last_name='Admin',
                        position='admin',
                        email='system@ibake.com',
                        salary=Decimal('1.00')
                    )
            
            for material_data in unused_materials_data:
                # Get the production detail for this material to get the correct unit
                production_detail = self.details.filter(raw_material_id=material_data['material_id']).first()
                correct_unit = production_detail.unit if production_detail else 'g'  # Use production unit, fallback to 'g'
                
                # Create the unused material return record
                unused_return = UnusedMaterialReturn.objects.create(
                    production=self,
                    raw_material_id=material_data['material_id'],
                    returned_quantity=material_data['quantity_returned'],
                    unit=material_data.get('unit', correct_unit),  # Use unit from frontend, fallback to production unit
                    return_reason=material_data.get('reason', 'Production cancelled'),
                    employee=employee,
                    notes=material_data.get('notes', '') + (f" | Return notes: {return_notes}" if return_notes else '')
                )

        total_consumed_cost = Decimal('0')
        waste_cost = Decimal('0')
        returned_cost = Decimal('0')
        
        # Group production details by material
        material_totals = {}
        
        for detail in self.details.all():
            material_id = detail.raw_material.id
            
            if material_id not in material_totals:
                material_totals[material_id] = {
                    'material': detail.raw_material,
                    'total_quantity': Decimal('0'),
                    'unit': detail.unit,
                    'unit_cost': self.get_standardized_unit_cost(detail.raw_material, detail.unit)
                }
            
            material_totals[material_id]['total_quantity'] += detail.quantity_used
        
        for material_data in material_totals.values():
            consumed_cost = material_data['total_quantity'] * material_data['unit_cost']
            total_consumed_cost += consumed_cost
        
        returned_materials = {}
        if unused_materials_data:
            for material_data in unused_materials_data:
                material_id = int(material_data['material_id'])
                returned_quantity = Decimal(str(material_data['quantity_returned']))
                returned_materials[material_id] = returned_quantity
        
        for material_id, material_data in material_totals.items():
            total_consumed = material_data['total_quantity']
            unit_cost = material_data['unit_cost']
            
            returned_quantity = returned_materials.get(material_id, Decimal('0'))
            
            if returned_quantity > total_consumed:
                returned_quantity = total_consumed
            
            wasted_quantity = total_consumed - returned_quantity
            
            if returned_quantity > 0:
                returned_cost += returned_quantity * unit_cost
            
            if wasted_quantity > 0:
                waste_cost += wasted_quantity * unit_cost

        if returned_cost > 0:
            try:
                from accounting.utils import create_journal_entry
                
                create_journal_entry(
                    description=f"Production #{self.production_number} - Materials Returned to Inventory",
                    transactions=[
                        {
                            'account_code': 'RAW_MAT',
                            'debit': returned_cost,
                            'credit': Decimal('0'),
                            'description': f'Materials returned from cancelled production #{self.production_number}'
                        },
                        {
                            'account_code': 'WIP',
                            'debit': Decimal('0'),
                            'credit': returned_cost,
                            'description': f'Work in Process returned to raw materials - Production #{self.production_number}'
                        }
                    ],
                    reference_type='material_return',
                    reference_id=self.id,
                    entry_date=None  # Use current date for real-time accuracy
                )
            except Exception as e:
                print(f"Material return journal entry error: {e}")
                import traceback
                traceback.print_exc()

        if waste_cost > 0:
            try:
                from accounting.utils import create_journal_entry
                
                transactions = [
                    {
                        'account_code': 'PROD_WASTE',
                        'debit': waste_cost,
                        'credit': Decimal('0'),
                        'description': f'Production waste from cancelled production #{self.production_number}'
                    },
                    {
                        'account_code': 'WIP',
                        'debit': Decimal('0'),
                        'credit': waste_cost,
                        'description': f'Work in Process written off as waste - Production #{self.production_number}'
                    }
                ]
                
                create_journal_entry(
                    description=f"Production #{self.production_number} - Waste from Cancellation",
                    transactions=transactions,
                    reference_type='production_waste',
                    reference_id=self.id,
                    entry_date=None  # Use current date for real-time accuracy
                )
            except Exception as e:
                print(f"Production waste journal entry error: {e}")
                import traceback
                traceback.print_exc()

        self.status = 'cancelled'
        self.save(update_fields=['status', 'wastage_notes'])
        
        # Build success message
        messages = []
        if returned_cost > 0:
            messages.append(f"₱{returned_cost:.2f} returned to raw materials")
        if waste_cost > 0:
            messages.append(f"₱{waste_cost:.2f} recorded as production waste expense")
        
        if messages:
            detail_message = f" {' and '.join(messages)}."
        else:
            detail_message = ""
            
        return True, f"Production cancelled successfully.{detail_message}"

class ProductionDetail(models.Model):
    production = models.ForeignKey(Production, on_delete=models.CASCADE, related_name='details')
    raw_material = models.ForeignKey(RawMaterial, on_delete=models.CASCADE)
    quantity_used = models.DecimalField(max_digits=10, decimal_places=2)
    unit = models.CharField(max_length=20)
    source_batch = models.ForeignKey('StockInDetail', on_delete=models.SET_NULL, null=True, blank=True)
    notes = models.TextField(blank=True)

    def __str__(self):
        return f"{self.production.production_number} - {self.raw_material.name}"

class StockIn(models.Model):
    PAYMENT_METHOD_CHOICES = [
        ('cash', 'Cash'),
        ('credit', 'Credit'),
    ]
    
    employee = models.ForeignKey('employee.Employee', on_delete=models.PROTECT)
    date = models.DateField(auto_now_add=True)
    reference_number = models.CharField(max_length=50, blank=True)
    payment_method = models.CharField(max_length=10, choices=PAYMENT_METHOD_CHOICES, default='credit')
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Stock In'
        verbose_name_plural = 'Stock Ins'
        ordering = ['-date', '-id']

    def __str__(self):
        return f"StockIn #{self.id} - {self.employee} - {self.date}"

class StockInDetail(models.Model):
    stock_in = models.ForeignKey(StockIn, on_delete=models.CASCADE, related_name='details')
    material = models.ForeignKey(RawMaterial, on_delete=models.PROTECT)
    unit = models.CharField(max_length=20)
    quantity = models.DecimalField(max_digits=10, decimal_places=2)
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)
    total_cost = models.DecimalField(max_digits=15, decimal_places=2)
    expiry_date = models.DateField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Stock In Detail'
        verbose_name_plural = 'Stock In Details'
        ordering = ['stock_in', 'material']

    def __str__(self):
        return f"{self.stock_in.id} - {self.material}"

    def save(self, *args, **kwargs):
        self.total_cost = self.quantity * self.unit_price
        super().save(*args, **kwargs)

class StockMovement(models.Model):
    MOVEMENT_TYPE_CHOICES = [
        ('IN', 'Stock In'),
        ('OUT', 'Stock Out'),
        ('ADJ', 'Adjustment'),
    ]
    
    movement_number = models.CharField(max_length=20, unique=True)
    date = models.DateField(auto_now_add=True)
    movement_type = models.CharField(max_length=10, choices=MOVEMENT_TYPE_CHOICES)
    raw_material = models.ForeignKey(RawMaterial, on_delete=models.SET_NULL, null=True, blank=True, related_name='stock_movements')
    finished_good = models.ForeignKey(FinishedGood, on_delete=models.SET_NULL, null=True, blank=True, related_name='stock_movements')
    quantity = models.DecimalField(max_digits=10, decimal_places=2)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Stock Movement'
        verbose_name_plural = 'Stock Movements'
        ordering = ['-date', '-movement_number']

    def __str__(self):
        product = self.raw_material or self.finished_good
        return f"{self.movement_number} - {product} ({self.get_movement_type_display()})"

class Product(models.Model):
    CATEGORY_CHOICES = [
        ('cake', 'Cake'),
        ('pastry', 'Pastry'),
        ('dessert', 'Dessert'),
        ('snack', 'Snack'),
        ('coffee', 'Coffee'),
        ('non-coffee', 'Non-coffee'),
    ]

    name = models.CharField(max_length=100)
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES)
    description = models.TextField(blank=True)
    base_price = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    selling_price = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    shelf_life = models.PositiveIntegerField(help_text='Shelf life in days', default=0)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Product'
        verbose_name_plural = 'Products'
        ordering = ['name']

    def __str__(self):
        return self.name 

class RawMaterialMovement(models.Model):
    MOVEMENT_TYPE_CHOICES = [
        ('IN', 'Stock In'),
        ('OUT', 'Stock Out'),
        ('ADJ', 'Adjustment'),
    ]
    
    movement_number = models.CharField(max_length=20, unique=True)
    date = models.DateField(default=get_current_date)
    movement_type = models.CharField(max_length=10, choices=MOVEMENT_TYPE_CHOICES)
    raw_material = models.ForeignKey(RawMaterial, on_delete=models.PROTECT, related_name='movements')
    quantity = models.DecimalField(max_digits=10, decimal_places=2)
    unit = models.CharField(max_length=20)
    remaining_quantity = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    reference = models.CharField(max_length=100, blank=True)  # e.g., Stock In ID, Production ID
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Raw Material Movement'
        verbose_name_plural = 'Raw Material Movements'
        ordering = ['date', 'movement_number']

    def __str__(self):
        return f"{self.movement_number} - {self.raw_material} ({self.get_movement_type_display()})"

    def save(self, *args, **kwargs):
        if not self.movement_number:
            # Generate movement number
            last_movement = RawMaterialMovement.objects.order_by('-movement_number').first()
            if last_movement and last_movement.movement_number.startswith('RMV'):
                try:
                    last_number = int(last_movement.movement_number[3:])
                    new_number = last_number + 1
                except ValueError:
                    new_number = 1
            else:
                new_number = 1
            self.movement_number = f'RMV{new_number:06d}'
        
        # Ensure date is properly set as today's date for new records
        if self.pk is None:  # New record
            self.date = get_current_date()
            
            if self.movement_type == 'IN':
                # For new IN movements, quantity should already be in base units
                # Set remaining_quantity equal to quantity since both are in base units
                self.remaining_quantity = self.quantity
                    
            elif self.movement_type == 'ADJ' and self.quantity > 0:
                # Positive adjustment (returns) - add to available stock
                # For returns, use the quantity as-is with NO conversion
                # The returned quantity should already be in base units
                self.remaining_quantity = self.quantity
            else:
                # OUT movements or negative adjustments don't add to remaining stock
                self.remaining_quantity = 0
        
        super().save(*args, **kwargs)

    @classmethod
    def deduct_stock_fifo(cls, raw_material, quantity_to_deduct, unit, reference='', notes=''):
        """
        Deduct stock using FIFO method.
        Returns True if successful, False if not enough stock.
        """
        # Get all IN movements with remaining stock, ordered by date (FIFO)
        movements = cls.objects.filter(
            raw_material=raw_material,
            movement_type__in=['IN', 'ADJ'],  # Include both IN and ADJ movements
            remaining_quantity__gt=0
        ).order_by('date')

        remaining_to_deduct = quantity_to_deduct
        deducted_movements = []

        for movement in movements:
            if remaining_to_deduct <= 0:
                break

            if movement.remaining_quantity >= remaining_to_deduct:
                movement.remaining_quantity -= remaining_to_deduct
                movement.save()
                deducted_movements.append((movement, remaining_to_deduct))
                remaining_to_deduct = 0
            else:
                remaining_to_deduct -= movement.remaining_quantity
                deducted_movements.append((movement, movement.remaining_quantity))
                movement.remaining_quantity = 0
                movement.save()

        if remaining_to_deduct > 0:
            # Not enough stock available
            return False

        # Create OUT movement record
        cls.objects.create(
            movement_type='OUT',
            raw_material=raw_material,
            quantity=quantity_to_deduct,
            unit=unit,
            reference=reference,
            notes=notes
        )

        return True

    @classmethod
    def get_available_stock(cls, raw_material):
        """
        Get total available stock for a raw material.
        Includes both IN movements and positive ADJ movements (returns).
        """
        total = cls.objects.filter(
            raw_material=raw_material,
            movement_type__in=['IN', 'ADJ'],
            remaining_quantity__gt=0
        ).aggregate(total=models.Sum('remaining_quantity'))['total'] or 0
        return total

    def display_quantity(self):
        """Return quantity in stock-in unit for display."""
        return self.raw_material.from_base_unit(self.quantity)
    
    def get_stock_status(self):
        """Get the stock status (FULL, PARTIAL, EXHAUSTED) for IN movements"""
        if self.movement_type != 'IN':
            return None
        
        if self.remaining_quantity == 0:
            return 'EXHAUSTED'
        
        # Both quantity and remaining_quantity are now in base units, so compare directly
        if self.remaining_quantity < self.quantity:
            return 'PARTIAL'
        else:
            return 'FULL'

class ProductionBatchProduct(models.Model):
    production = models.ForeignKey(Production, related_name='batch_products', on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.PROTECT)
    quantity = models.DecimalField(max_digits=10, decimal_places=2)
    unit = models.CharField(max_length=20)

class FinishedGoodsInventory(models.Model):
    """
    Tracks finished goods with FEFO (First Expired First Out) system
    """
    batch_number = models.CharField(max_length=20, unique=True, blank=True)
    product = models.ForeignKey(Product, on_delete=models.PROTECT, related_name='finished_inventory')
    production = models.ForeignKey(Production, on_delete=models.PROTECT, related_name='finished_goods')
    quantity = models.DecimalField(max_digits=10, decimal_places=2)
    remaining_quantity = models.DecimalField(max_digits=10, decimal_places=2)
    production_date = models.DateField()
    expiry_date = models.DateField()
    unit = models.CharField(max_length=20, default='pcs')
    status = models.CharField(max_length=20, choices=[
        ('available', 'Available'),
        ('expired', 'Expired'),
        ('consumed', 'Fully Consumed')
    ], default='available')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Finished Goods Inventory'
        verbose_name_plural = 'Finished Goods Inventory'
        ordering = ['expiry_date', 'production_date']  # FEFO ordering

    def __str__(self):
        return f"{self.batch_number} - {self.product.name} (Exp: {self.expiry_date})"

    def save(self, *args, **kwargs):
        if not self.batch_number:
            # Generate batch number: BATCH-YYYYMMDD-XXX
            today = get_current_date()
            date_str = today.strftime('%Y%m%d')
            
            # Find the highest batch number for today
            today_batches = FinishedGoodsInventory.objects.filter(
                batch_number__startswith=f'BATCH-{date_str}'
            ).order_by('-batch_number')
            
            if today_batches.exists():
                last_batch = today_batches.first().batch_number
                last_number = int(last_batch.split('-')[-1])
                new_number = last_number + 1
            else:
                new_number = 1
                
            self.batch_number = f'BATCH-{date_str}-{new_number:03d}'
        
        # Set remaining_quantity if not provided
        if self.remaining_quantity is None:
            self.remaining_quantity = self.quantity
            
        # Calculate expiry date if not provided
        if not self.expiry_date and self.production_date and self.product.shelf_life:
            from datetime import timedelta
            self.expiry_date = self.production_date + timedelta(days=self.product.shelf_life)
            
        super().save(*args, **kwargs)

    @classmethod
    def consume_fefo(cls, product, quantity_to_consume, reference='', notes=''):
        """
        Consume finished goods using FEFO (First Expired First Out) method.
        Returns list of consumed batches or None if insufficient stock.
        """
        # Get available batches ordered by expiry date (FEFO)
        available_batches = cls.objects.filter(
            product=product,
            status='available',
            remaining_quantity__gt=0
        ).order_by('expiry_date', 'production_date')

        remaining_to_consume = quantity_to_consume
        consumed_batches = []

        for batch in available_batches:
            if remaining_to_consume <= 0:
                break

            if batch.remaining_quantity >= remaining_to_consume:
                # This batch can fulfill the remaining requirement
                batch.remaining_quantity -= remaining_to_consume
                consumed_batches.append({
                    'batch': batch,
                    'quantity_consumed': remaining_to_consume
                })
                remaining_to_consume = 0
                
                if batch.remaining_quantity == 0:
                    batch.status = 'consumed'
                batch.save()
            else:
                # Consume entire batch
                consumed_batches.append({
                    'batch': batch,
                    'quantity_consumed': batch.remaining_quantity
                })
                remaining_to_consume -= batch.remaining_quantity
                batch.remaining_quantity = 0
                batch.status = 'consumed'
                batch.save()

        if remaining_to_consume > 0:
            # Not enough stock available
            return None

        return consumed_batches

    @classmethod
    def check_and_expire_goods(cls, as_of_date=None):
        """
        Check for expired goods and write them off with proper accounting
        Returns list of expired batches processed
        """
        from django.utils import timezone
        from decimal import Decimal
        
        if as_of_date is None:
            as_of_date = get_current_date()
        
        # Find goods that are expired but still marked as available
        expired_goods = cls.objects.filter(
            expiry_date__lt=as_of_date,
            status='available',
            remaining_quantity__gt=0
        )
        
        expired_batches = []
        total_loss_value = Decimal('0')
        
        for batch in expired_goods:
            # Calculate cost of expired goods
            from accounting.utils import calculate_product_cost
            cost_per_unit = calculate_product_cost(batch.product)
            loss_value = batch.remaining_quantity * cost_per_unit
            total_loss_value += loss_value
            
            expired_batches.append({
                'batch': batch,
                'expired_quantity': batch.remaining_quantity,
                'loss_value': loss_value,
                'expiry_date': batch.expiry_date
            })
            
            # Mark as expired and zero out remaining quantity
            batch.status = 'expired'
            batch.remaining_quantity = 0
            batch.save()
        
        if total_loss_value > 0:
            try:
                from accounting.utils import create_journal_entry
                
                batch_numbers = [item['batch'].batch_number for item in expired_batches]
                description = f"Write-off of expired finished goods - Batches: {', '.join(batch_numbers[:3])}"
                if len(batch_numbers) > 3:
                    description += f" and {len(batch_numbers) - 3} more"
                
                create_journal_entry(
                    description=description,
                    transactions=[
                        {
                            'account_code': 'EXP_GOODS',  # Loss on Expired Goods expense account
                            'debit': total_loss_value,
                            'credit': Decimal('0'),
                            'description': f'Loss on expired finished goods - {len(expired_batches)} batches'
                        },
                        {
                            'account_code': 'FIN_GOODS',  # Finished Goods Inventory
                            'debit': Decimal('0'),
                            'credit': total_loss_value,
                            'description': f'Write-off expired inventory - {len(expired_batches)} batches'
                        }
                    ],
                    reference_type='expired_goods',
                    reference_id=None,
                    entry_date=as_of_date
                )
                
            except Exception as e:
                print(f"Error creating expired goods journal entry: {e}")
                import traceback
                traceback.print_exc()
        
        return expired_batches

    @classmethod
    def get_expiring_soon(cls, days_ahead=3):
        """Get goods expiring within specified days"""
        from django.utils import timezone
        from datetime import timedelta
        
        cutoff_date = get_current_date() + timedelta(days=days_ahead)
        
        return cls.objects.filter(
            status='available',
            remaining_quantity__gt=0,
            expiry_date__lte=cutoff_date
        ).order_by('expiry_date')

    @classmethod
    def get_available_stock(cls, product):
        """Get total available stock for a product"""
        return cls.objects.filter(
            product=product,
            status='available'
        ).aggregate(
            total=models.Sum('remaining_quantity')
        )['total'] or Decimal('0')

class MaterialSufficiencyCheck(models.Model):
    """
    Tracks material sufficiency check for production batches
    """
    production = models.ForeignKey(Production, on_delete=models.CASCADE, related_name='sufficiency_checks')
    raw_material = models.ForeignKey(RawMaterial, on_delete=models.PROTECT)
    required_quantity = models.DecimalField(max_digits=10, decimal_places=2)
    available_quantity = models.DecimalField(max_digits=10, decimal_places=2)
    is_sufficient = models.BooleanField()
    unit = models.CharField(max_length=20)
    checked_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = 'Material Sufficiency Check'
        verbose_name_plural = 'Material Sufficiency Checks'
        unique_together = ['production', 'raw_material']

    def __str__(self):
        status = "✓ Sufficient" if self.is_sufficient else "✗ Insufficient"
        return f"{self.production.production_number} - {self.raw_material.name}: {status}"

class UnusedMaterialReturn(models.Model):
    """
    Tracks unused materials returned to inventory when production is cancelled
    """
    production = models.ForeignKey(Production, on_delete=models.CASCADE, related_name='unused_returns')
    raw_material = models.ForeignKey(RawMaterial, on_delete=models.PROTECT)
    returned_quantity = models.DecimalField(max_digits=10, decimal_places=2)
    unit = models.CharField(max_length=20)
    return_reason = models.CharField(max_length=255, default='Production cancelled')
    employee = models.ForeignKey('employee.Employee', on_delete=models.PROTECT)
    movement = models.ForeignKey(RawMaterialMovement, on_delete=models.SET_NULL, null=True, blank=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = 'Unused Material Return'
        verbose_name_plural = 'Unused Material Returns'

    def __str__(self):
        return f"{self.production.production_number} - Return {self.raw_material.name}: {self.returned_quantity}"

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        
        # Create adjustment movement to return material to inventory
        if not self.movement:
            # Get the original production details to find source batch and expiry info
            production_detail = ProductionDetail.objects.filter(
                production=self.production,
                raw_material=self.raw_material
            ).first()
            
            # Find source batch expiry date if available
            source_expiry_date = None
            if production_detail and production_detail.source_batch:
                source_expiry_date = production_detail.source_batch.expiry_date
            
            # Use the actual returned unit and quantity - no conversion needed
            # The frontend now sends the correct unit that matches the production detail
            return_quantity = self.returned_quantity
            return_unit = self.unit  # Use the actual unit from the return record
            
            # Create ADJ movement - add the returned amount back to inventory
            self.movement = RawMaterialMovement.objects.create(
                movement_type='ADJ',
                raw_material=self.raw_material,
                quantity=return_quantity,  # Use actual returned quantity
                unit=return_unit,  # Use actual returned unit
                reference=f'Return from Production #{self.production.production_number}',
                notes=f'Returned material from cancelled production' + 
                      (f' | Expiry: {source_expiry_date}' if source_expiry_date else '')
            )
            
            self.save(update_fields=['movement']) 