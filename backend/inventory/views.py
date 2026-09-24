from django.shortcuts import render, get_object_or_404, redirect
from django.urls import reverse_lazy
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import ListView, CreateView, UpdateView, DeleteView, DetailView, View
from .models import RawMaterial, FinishedGood, StockMovement, ProductRecipe, Product, StockIn, StockInDetail, ProductRecipeDetail, RawMaterialMovement, Production, ProductionDetail, ProductionBatchProduct, FinishedGoodsInventory, MaterialSufficiencyCheck, UnusedMaterialReturn
from .forms import RawMaterialForm, FinishedGoodForm, StockMovementForm, ProductRecipeForm, ProductForm, StockInForm, StockInDetailForm, ProductRecipeDetailFormSet, RawMaterialMovementForm, ProductionForm, ProductionDetailForm, ProductionBatchProductFormSet, RawMaterialInventoryFilterForm
from django.forms import inlineformset_factory
from django.contrib import messages
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
import json
from django.template.loader import render_to_string
from django.views.decorators.http import require_POST
from decimal import Decimal, InvalidOperation
from django.core.serializers.json import DjangoJSONEncoder
from django.db.models import F, Sum, Min, ProtectedError
from django.utils.decorators import method_decorator
from django.utils import timezone
from datetime import timedelta
from accounting.utils import create_journal_entry
from core.datetime_utils import get_current_date, get_current_datetime

class RawMaterialListView(LoginRequiredMixin, ListView):
    model = RawMaterial
    template_name = 'inventory/raw_material_list.html'
    context_object_name = 'materials'

class RawMaterialCreateView(LoginRequiredMixin, CreateView):
    model = RawMaterial
    form_class = RawMaterialForm
    template_name = 'inventory/raw_material_form.html'
    success_url = reverse_lazy('inventory:raw_material_list')

class RawMaterialUpdateView(LoginRequiredMixin, UpdateView):
    model = RawMaterial
    form_class = RawMaterialForm
    template_name = 'inventory/raw_material_form.html'
    success_url = reverse_lazy('inventory:raw_material_list')

class RawMaterialDeleteView(LoginRequiredMixin, DeleteView):
    model = RawMaterial
    template_name = 'inventory/raw_material_confirm_delete.html'
    success_url = reverse_lazy('inventory:raw_material_list')

    def delete(self, request, *args, **kwargs):
        self.object = self.get_object()
        success_url = self.get_success_url()
        try:
            self.object.delete()
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({'status': 'success'})
            return redirect(success_url)
        except ProtectedError:
            error_msg = 'Cannot delete: This raw material is used in other records.'
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({'status': 'error', 'error': error_msg}, status=400)
            messages.error(request, error_msg)
            return redirect(success_url)

class FinishedGoodListView(LoginRequiredMixin, ListView):
    model = FinishedGood
    template_name = 'inventory/finished_good_list.html'
    context_object_name = 'goods'

class FinishedGoodCreateView(LoginRequiredMixin, CreateView):
    model = FinishedGood
    form_class = FinishedGoodForm
    template_name = 'inventory/finished_good_form.html'
    success_url = reverse_lazy('inventory:finished_good_list')

class FinishedGoodUpdateView(LoginRequiredMixin, UpdateView):
    model = FinishedGood
    form_class = FinishedGoodForm
    template_name = 'inventory/finished_good_form.html'
    success_url = reverse_lazy('inventory:finished_good_list')

class FinishedGoodDeleteView(LoginRequiredMixin, DeleteView):
    model = FinishedGood
    template_name = 'inventory/finished_good_confirm_delete.html'
    success_url = reverse_lazy('inventory:finished_good_list')

class StockMovementListView(LoginRequiredMixin, ListView):
    model = StockMovement
    template_name = 'inventory/stock_movement_list.html'
    context_object_name = 'movements'
    ordering = ['-created_at']

class StockMovementCreateView(LoginRequiredMixin, CreateView):
    model = StockMovement
    form_class = StockMovementForm
    template_name = 'inventory/stock_movement_form.html'
    success_url = reverse_lazy('inventory:stock_movement_list')

class ProductRecipeListView(LoginRequiredMixin, ListView):
    model = ProductRecipe
    template_name = 'inventory/product_recipe_list.html'
    context_object_name = 'recipes'

class ProductRecipeCreateView(LoginRequiredMixin, CreateView):
    model = ProductRecipe
    form_class = ProductRecipeForm
    template_name = 'inventory/product_recipe_form.html'
    success_url = reverse_lazy('inventory:product_recipe_list')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['materials'] = list(RawMaterial.objects.values('id', 'name', 'brand'))
        return context

    def form_valid(self, form):
        self.object = form.save()
        details_json = self.request.POST.get('recipe_details_json')
        if details_json:
            try:
                details = json.loads(details_json)
                for detail in details:
                    ProductRecipeDetail.objects.create(
                        recipe=self.object,
                        material_id=detail['material'],
                        unit=detail['unit'],
                        quantity=detail['quantity']
                    )
            except Exception as e:
                messages.error(self.request, f'Error saving recipe details: {e}')
        messages.success(self.request, 'Recipe created successfully.')
        return redirect(self.success_url)

class ProductRecipeUpdateView(LoginRequiredMixin, UpdateView):
    model = ProductRecipe
    form_class = ProductRecipeForm
    template_name = 'inventory/product_recipe_form.html'
    success_url = reverse_lazy('inventory:product_recipe_list')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['materials'] = list(RawMaterial.objects.values('id', 'name', 'brand'))
        # Pass existing details as JSON for JS prefill
        details = list(self.object.details.values('material_id', 'unit', 'quantity'))
        context['details_json'] = json.dumps(details, cls=DjangoJSONEncoder)
        return context

    def form_valid(self, form):
        self.object = form.save()
        details_json = self.request.POST.get('recipe_details_json')
        if details_json:
            try:
                details = json.loads(details_json)
                # Remove old details
                self.object.details.all().delete()
                for detail in details:
                    ProductRecipeDetail.objects.create(
                        recipe=self.object,
                        material_id=detail['material'],
                        unit=detail['unit'],
                        quantity=detail['quantity']
                    )
            except Exception as e:
                messages.error(self.request, f'Error saving recipe details: {e}')
        messages.success(self.request, 'Recipe updated successfully.')
        return redirect(self.success_url)

class ProductRecipeDeleteView(LoginRequiredMixin, DeleteView):
    model = ProductRecipe
    template_name = 'inventory/product_recipe_confirm_delete.html'
    success_url = reverse_lazy('inventory:product_recipe_list')

    def delete(self, request, *args, **kwargs):
        messages.success(request, 'Recipe deleted successfully.')
        return super().delete(request, *args, **kwargs)

class ProductListView(LoginRequiredMixin, ListView):
    model = Product
    template_name = 'inventory/product_list.html'
    context_object_name = 'products'

class ProductCreateView(LoginRequiredMixin, CreateView):
    model = Product
    form_class = ProductForm
    template_name = 'inventory/product_form.html'
    success_url = reverse_lazy('inventory:product_list')

class ProductUpdateView(LoginRequiredMixin, UpdateView):
    model = Product
    form_class = ProductForm
    template_name = 'inventory/product_form.html'
    success_url = reverse_lazy('inventory:product_list')

class ProductDeleteView(LoginRequiredMixin, DeleteView):
    model = Product
    template_name = 'inventory/product_confirm_delete.html'
    success_url = reverse_lazy('inventory:product_list')

class StockInListView(ListView):
    model = StockIn
    template_name = 'inventory/stockin_list.html'
    context_object_name = 'stockins'

from django.views import View

class StockInCreateView(View):
    def get(self, request):
        stockin_form = StockInForm()
        StockInDetailFormSet = inlineformset_factory(StockIn, StockInDetail, form=StockInDetailForm, extra=1, can_delete=True)
        formset = StockInDetailFormSet()
        materials = RawMaterial.objects.all()
        return render(request, 'inventory/stockin_form.html', {
            'form': stockin_form,
            'formset': formset,
            'title': 'Add Stock In',
            'materials': materials
        })

    def post(self, request):
        stockin_form = StockInForm(request.POST)
        materials = RawMaterial.objects.all()
        if stockin_form.is_valid():
            stockin = stockin_form.save()
            # Parse details from hidden input
            details_json = request.POST.get('stockin_details_json')
            total_cost = 0
            if details_json:
                try:
                    details = json.loads(details_json)
                    for detail in details:
                        try:
                            quantity = Decimal(str(detail['quantity']))
                            unit_price = Decimal(str(detail['unit_price']))
                        except (InvalidOperation, KeyError, TypeError) as e:
                            messages.error(request, f"Invalid input for quantity or unit price: {detail} ({e})")
                            continue
                        expiry = detail.get('expiry_date') or None
                        material = RawMaterial.objects.get(id=detail['material'])
                        detail_obj = StockInDetail.objects.create(
                            stock_in=stockin,
                            material_id=detail['material'],
                            unit=detail['unit'],
                            quantity=quantity,
                            unit_price=unit_price,
                            total_cost=quantity * unit_price,
                            expiry_date=expiry
                        )
                        total_cost += detail_obj.total_cost
                        # Convert quantity to base units for consistent storage
                        base_quantity = material.to_base_unit(quantity)
                        RawMaterialMovement.objects.create(
                            movement_type='IN',
                            raw_material=detail_obj.material,
                            quantity=base_quantity,  # Store in base units
                            unit=material.base_unit,  # Use base unit
                            reference=f'StockIn #{stockin.id}',
                            notes=f'Expiry: {detail_obj.expiry_date}' if detail_obj.expiry_date else '',
                        )
                    
                    messages.success(request, f'Stock In record created successfully. Total: ₱{total_cost:,.2f}')
                    
                    # Create automatic journal entries for stock in
                    if total_cost > 0:
                        try:
                            # Ensure total_cost is Decimal
                            total_cost_decimal = Decimal(str(total_cost))
                            
                            # Determine second account based on payment method
                            if stockin.payment_method == 'cash':
                                credit_account = 'CASH'
                                payment_description = f'Cash payment for materials - Stock In #{stockin.id}'
                            else:  # credit
                                credit_account = 'ACCT_PAY'
                                payment_description = f'Amount owed to supplier - Stock In #{stockin.id}'
                            
                            journal_entry = create_journal_entry(
                                description=f"Stock In #{stockin.id} - Material Purchase ({stockin.get_payment_method_display()})",
                                transactions=[
                                    {
                                        'account_code': 'RAW_MAT',
                                        'debit': total_cost_decimal,
                                        'credit': Decimal('0'),
                                        'description': f'Materials received - Stock In #{stockin.id}'
                                    },
                                    {
                                        'account_code': credit_account,
                                        'debit': Decimal('0'),
                                        'credit': total_cost_decimal,
                                        'description': payment_description
                                    }
                                ],
                                reference_type='stock_in',
                                reference_id=stockin.id,
                                entry_date=stockin.date
                            )
                            
                            messages.success(request, f'Stock In record and journal entry {journal_entry.entry_number} created successfully. Total: ₱{total_cost:,.2f}')
                        except Exception as e:
                            # Also log the full traceback for debugging
                            import traceback
                            print(f"Stock In journal entry error: {e}")
                            print(traceback.format_exc())
                            messages.warning(request, f'Stock In created but journal entry failed: {e}')
                    else:
                        messages.success(request, 'Stock In record created successfully.')
                except Exception as e:
                    messages.error(request, f'Error saving details: {e}')
            else:
                messages.success(request, 'Stock In record created successfully.')
            return redirect('inventory:stockin_list')
        # fallback: render form with errors
        StockInDetailFormSet = inlineformset_factory(StockIn, StockInDetail, form=StockInDetailForm, extra=1, can_delete=True)
        formset = StockInDetailFormSet(request.POST)
        return render(request, 'inventory/stockin_form.html', {
            'form': stockin_form,
            'formset': formset,
            'title': 'Add Stock In',
            'materials': materials
        })

class StockInUpdateView(View):
    def get(self, request, pk):
        stockin = get_object_or_404(StockIn, pk=pk)
        stockin_form = StockInForm(instance=stockin)
        StockInDetailFormSet = inlineformset_factory(StockIn, StockInDetail, form=StockInDetailForm, extra=0, can_delete=True)
        formset = StockInDetailFormSet(instance=stockin)
        materials = RawMaterial.objects.all()
        # Prepare details for JS prefill, include expiry_date
        details = list(stockin.details.values('material_id', 'unit', 'quantity', 'unit_price', 'expiry_date'))
        # Convert expiry_date to string for JSON serialization
        for d in details:
            if d['expiry_date']:
                d['expiry_date'] = d['expiry_date'].strftime('%Y-%m-%d')
        details_json = json.dumps(details, cls=DjangoJSONEncoder)
        return render(request, 'inventory/stockin_form.html', {
            'form': stockin_form,
            'formset': formset,
            'title': 'Edit Stock In',
            'materials': materials,
            'details_json': details_json
        })

    def post(self, request, pk):
        stockin = get_object_or_404(StockIn, pk=pk)
        stockin_form = StockInForm(request.POST, instance=stockin)
        materials = RawMaterial.objects.all()
        if stockin_form.is_valid():
            stockin = stockin_form.save()
            
            # Parse details from hidden input
            details_json = request.POST.get('stockin_details_json')
            total_cost = 0
            if details_json:
                try:
                    details = json.loads(details_json)
                    # Remove old details and movements
                    stockin.details.all().delete()
                    # Also remove related raw material movements
                    from .models import RawMaterialMovement
                    RawMaterialMovement.objects.filter(reference=f'StockIn #{stockin.id}').delete()
                    
                    for detail in details:
                        try:
                            quantity = Decimal(str(detail['quantity']))
                            unit_price = Decimal(str(detail['unit_price']))
                            expiry = detail.get('expiry_date') or None
                            material = RawMaterial.objects.get(id=detail['material'])
                            detail_obj = StockInDetail.objects.create(
                                stock_in=stockin,
                                material_id=detail['material'],
                                unit=detail['unit'],
                                quantity=quantity,
                                unit_price=unit_price,
                                total_cost=quantity * unit_price,
                                expiry_date=expiry
                            )
                            total_cost += detail_obj.total_cost
                            # Convert quantity to base units for consistent storage
                            base_quantity = material.to_base_unit(quantity)
                            RawMaterialMovement.objects.create(
                                movement_type='IN',
                                raw_material=detail_obj.material,
                                quantity=base_quantity,  # Store in base units
                                unit=material.base_unit,  # Use base unit
                                reference=f'StockIn #{stockin.id}',
                                notes=f'Expiry: {detail_obj.expiry_date}' if detail_obj.expiry_date else '',
                            )
                        except (InvalidOperation, KeyError, TypeError) as e:
                            messages.error(request, f"Invalid input for quantity or unit price: {detail} ({e})")
                            continue
                    
                    messages.success(request, f'Stock In record updated successfully. Total: ₱{total_cost:,.2f}')
                    
                    # Handle journal entries for updated stock in
                    # First, delete any existing journal entries for this stock in to avoid duplicates
                    from accounting.models import JournalEntry
                    existing_entries = JournalEntry.objects.filter(
                        reference_type='stock_in',
                        reference_id=stockin.id
                    )
                    if existing_entries.exists():
                        existing_entries.delete()
                    
                    # Create new journal entry for updated stock in
                    if total_cost > 0:
                        try:
                            # Ensure total_cost is Decimal
                            total_cost_decimal = Decimal(str(total_cost))
                            
                            # Determine second account based on payment method
                            if stockin.payment_method == 'cash':
                                credit_account = 'CASH'
                                payment_description = f'Cash payment for materials - Stock In #{stockin.id}'
                            else:  # credit
                                credit_account = 'ACCT_PAY'
                                payment_description = f'Amount owed to supplier - Stock In #{stockin.id}'
                            
                            journal_entry = create_journal_entry(
                                description=f"Stock In #{stockin.id} - Material Purchase ({stockin.get_payment_method_display()})",
                                transactions=[
                                    {
                                        'account_code': 'RAW_MAT',
                                        'debit': total_cost_decimal,
                                        'credit': Decimal('0'),
                                        'description': f'Materials received - Stock In #{stockin.id}'
                                    },
                                    {
                                        'account_code': credit_account,
                                        'debit': Decimal('0'),
                                        'credit': total_cost_decimal,
                                        'description': payment_description
                                    }
                                ],
                                reference_type='stock_in',
                                reference_id=stockin.id,
                                entry_date=stockin.date
                            )
                            
                            messages.success(request, f'Stock In record and journal entry {journal_entry.entry_number} updated successfully. Total: ₱{total_cost:,.2f}')
                        except Exception as e:
                            # Also log the full traceback for debugging
                            import traceback
                            print(f"Stock In journal entry error: {e}")
                            print(traceback.format_exc())
                            messages.warning(request, f'Stock In updated but journal entry failed: {e}')
                    else:
                        messages.success(request, 'Stock In record updated successfully.')
                except Exception as e:
                    messages.error(request, f'Error saving details: {e}')
            else:
                messages.success(request, 'Stock In record updated successfully.')
            return redirect('inventory:stockin_list')
        # fallback: render form with errors
        StockInDetailFormSet = inlineformset_factory(StockIn, StockInDetail, form=StockInDetailForm, extra=0, can_delete=True)
        formset = StockInDetailFormSet(request.POST, instance=stockin)
        return render(request, 'inventory/stockin_form.html', {
            'form': stockin_form,
            'formset': formset,
            'title': 'Edit Stock In',
            'materials': materials
        })

@csrf_exempt
def ajax_add_material(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            name = data.get('name')
            brand = data.get('brand', '')
            description = data.get('description', '')
            category = data.get('category')
            unit = data.get('unit')
            minimum_stock = data.get('minimum_stock', 0)
            unit_cost = data.get('unit_cost', 0)
            if not name or not category or not unit or unit_cost is None:
                return JsonResponse({'success': False, 'error': 'Missing required fields.'})
            material = RawMaterial.objects.create(
                name=name,
                brand=brand,
                description=description,
                category=category,
                unit=unit,
                minimum_stock=minimum_stock,
                unit_cost=unit_cost
            )
            return JsonResponse({'success': True, 'material': {
                'pk': material.pk,
                'name': material.name,
                'brand': material.brand,
                'unit': material.unit,
                'unit_cost': str(material.unit_cost)
            }})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
    return JsonResponse({'success': False, 'error': 'Invalid request.'})

@login_required
def ajax_stockin_details(request, pk):
    stockin = get_object_or_404(StockIn, pk=pk)
    details = []
    for d in stockin.details.select_related('material').all():
        total_stock = d.quantity * d.material.unit_conversion_factor
        # Format total_stock to remove trailing zeros and decimal point if not needed
        total_stock_str = (str(int(total_stock)) if total_stock == int(total_stock) else str(total_stock.normalize()))
        details.append({
            'material': d.material,
            'unit': d.unit,
            'quantity': d.quantity,
            'unit_price': d.unit_price,
            'expiry_date': d.expiry_date,
            'total_cost': d.total_cost,
            'total_stock': total_stock_str,
            'base_unit': d.material.base_unit,
        })
    html = render_to_string('inventory/stockin_details_modal.html', {
        'stockin': stockin,
        'details': details
    })
    return JsonResponse({'html': html})

@login_required
@require_POST
def ajax_stockin_delete(request, pk):
    stockin = get_object_or_404(StockIn, pk=pk)
    
    # Delete associated journal entries if they exist
    from accounting.models import JournalEntry
    existing_entries = JournalEntry.objects.filter(
        reference_type='stock_in',
        reference_id=stockin.id
    )
    if existing_entries.exists():
        existing_entries.delete()
    
    # Delete associated raw material movements
    from .models import RawMaterialMovement
    RawMaterialMovement.objects.filter(reference=f'StockIn #{stockin.id}').delete()
    
    stockin.delete()
    return JsonResponse({'success': True})

@login_required
def ajax_recipe_details(request, pk):
    recipe = get_object_or_404(ProductRecipe, pk=pk)
    details = recipe.details.select_related('material').all()
    html = render_to_string('inventory/recipe_details_modal.html', {
        'recipe': recipe,
        'details': details
    })
    return JsonResponse({'html': html})

class RawMaterialMovementListView(LoginRequiredMixin, ListView):
    model = RawMaterialMovement
    template_name = 'inventory/raw_material_movement_list.html'
    context_object_name = 'movements'
    ordering = ['-date', '-movement_number']
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Add debugging information about movement types
        in_movements_count = RawMaterialMovement.objects.filter(movement_type='IN').count()
        out_movements_count = RawMaterialMovement.objects.filter(movement_type='OUT').count()
        adj_movements_count = RawMaterialMovement.objects.filter(movement_type='ADJ').count()
        
        context['movement_stats'] = {
            'in_count': in_movements_count,
            'out_count': out_movements_count,
            'adj_count': adj_movements_count,
            'total_count': in_movements_count + out_movements_count + adj_movements_count
        }
        
        return context

class RawMaterialMovementCreateView(LoginRequiredMixin, CreateView):
    model = RawMaterialMovement
    form_class = RawMaterialMovementForm
    template_name = 'inventory/raw_material_movement_form.html'
    success_url = reverse_lazy('inventory:raw_material_movement_list')

class RawMaterialMovementUpdateView(LoginRequiredMixin, UpdateView):
    model = RawMaterialMovement
    form_class = RawMaterialMovementForm
    template_name = 'inventory/raw_material_movement_form.html'
    success_url = reverse_lazy('inventory:raw_material_movement_list')

class RawMaterialMovementDeleteView(LoginRequiredMixin, DeleteView):
    model = RawMaterialMovement
    template_name = 'inventory/raw_material_movement_confirm_delete.html'
    success_url = reverse_lazy('inventory:raw_material_movement_list')

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        self.object.delete()
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'status': 'success'})
        return redirect(self.success_url)

    def delete(self, request, *args, **kwargs):
        self.object = self.get_object()
        self.object.delete()
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'status': 'success'})
        return redirect(self.success_url)

class RawMaterialInventoryStatusView(LoginRequiredMixin, ListView):
    model = RawMaterial
    template_name = 'inventory/raw_material_inventory_status.html'
    context_object_name = 'materials'

    def get_queryset(self):
        qs = super().get_queryset().select_related()
        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Add filter form
        filter_form = RawMaterialInventoryFilterForm(self.request.GET)
        context['filter_form'] = filter_form
        
        materials = context['materials']
        inventory_data = []
        from .models import RawMaterialMovement, StockInDetail, ProductionDetail
        from django.db.models import Sum
        
        for material in materials:
            # Get current stock using RawMaterialMovement (IN - OUT - ADJ)
            current_stock = RawMaterialMovement.get_available_stock(material)
            
            # Get soonest expiry date among available batches (calculate remaining quantity properly)
            soonest_expiry = None
            stock_details = StockInDetail.objects.filter(
                material=material,
                expiry_date__isnull=False
            ).order_by('expiry_date')
            
            for stock_detail in stock_details:
                consumed_from_batch = ProductionDetail.objects.filter(
                    source_batch=stock_detail,
                    raw_material=material
                ).aggregate(
                    total_consumed=Sum('quantity_used')
                )['total_consumed'] or 0
                
                remaining_in_batch = stock_detail.quantity - consumed_from_batch
                
                if remaining_in_batch > 0:
                    soonest_expiry = stock_detail.expiry_date
                    break
            
            # Determine status
            if current_stock > material.minimum_stock:
                status = 'Sufficient'
                status_key = 'sufficient'
            elif current_stock == material.minimum_stock and current_stock > 0:
                status = 'Low'
                status_key = 'low'
            elif current_stock == 0:
                status = 'Out of Stock'
                status_key = 'out_of_stock'
            else:
                status = 'Low'
                status_key = 'low'
                
            inventory_data.append({
                'material': material,
                'current_stock': current_stock,
                'minimum_stock': material.minimum_stock,
                'status': status,
                'status_key': status_key,
                'soonest_expiry': soonest_expiry
            })
        
        if filter_form.is_valid():
            search_query = filter_form.cleaned_data.get('search')
            status_filter = filter_form.cleaned_data.get('status')
            category_filter = filter_form.cleaned_data.get('category')
            
            if search_query:
                inventory_data = [
                    item for item in inventory_data 
                    if search_query.lower() in item['material'].name.lower() or 
                       (item['material'].brand and search_query.lower() in item['material'].brand.lower())
                ]
            
            if status_filter:
                inventory_data = [item for item in inventory_data if item['status_key'] == status_filter]
            
            if category_filter:
                inventory_data = [item for item in inventory_data if item['material'].category == category_filter]
        
        context['inventory_data'] = inventory_data
        return context

class ProductionListView(ListView):
    model = Production
    template_name = 'inventory/production_list.html'
    context_object_name = 'productions'

class ProductionCreateView(CreateView):
    model = Production
    form_class = ProductionForm
    template_name = 'inventory/production_form.html'
    success_url = reverse_lazy('inventory:production_list')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if self.request.POST:
            context['batch_formset'] = ProductionBatchProductFormSet(self.request.POST, prefix='batch_products')
        else:
            context['batch_formset'] = ProductionBatchProductFormSet(prefix='batch_products')
        
        # Add products for batch dropdown
        context['products'] = Product.objects.filter(is_active=True).order_by('name')
        
        return context

    def form_invalid(self, form):
        return super().form_invalid(form)

    def post(self, request, *args, **kwargs):
        try:
            return super().post(request, *args, **kwargs)
        except Exception as e:
            import traceback
            traceback.print_exc()
            messages.error(request, f"An error occurred: {str(e)}")
            return self.form_invalid(self.get_form())

    def form_valid(self, form):
        context = self.get_context_data()
        batch_formset = context['batch_formset']
        
        if not form.instance.can_edit():
            messages.error(self.request, 'Cannot edit production in current status.')
            return self.form_invalid(form)
            
        if batch_formset.is_valid():
            self.object = form.save(commit=False)
            
            # Automatically set status and date_started for new workflow
            if 'confirm_production' in self.request.POST:
                self.object.save()
                batch_formset.instance = self.object
                batch_formset.save()
                
                # Check material sufficiency
                sufficiency_result = self.object.check_material_sufficiency()
                
                if not sufficiency_result['sufficient']:
                    # Materials insufficient - delete the production and show error
                    insufficient_materials = [
                        f"{check.raw_material.name}: missing {(check.required_quantity - check.available_quantity):.2f} {check.unit}"
                        for check in sufficiency_result['checks'] 
                        if not check.is_sufficient
                    ]
                    error_message = f"Cannot start production - insufficient materials: {', '.join(insufficient_materials)}"
                    
                    # Clean up - delete the production we just created
                    production_number = self.object.production_number
                    self.object.delete()
                    
                    messages.error(self.request, error_message)
                    return redirect('inventory:production_list')
                
                # Materials are sufficient - proceed with starting production
                self.object.status = 'in_progress'
                self.object.date_started = get_current_date()
                self.object.save()
                
                # Call start_production to deduct raw materials inventory using FEFO
                success, message = self.object.start_production()
                if success:
                    messages.success(self.request, f'Production {self.object.production_number} started successfully! Raw materials have been deducted from inventory.')
                else:
                    # This should not happen since we checked sufficiency, but handle gracefully
                    messages.error(self.request, f'Error starting production: {message}')
                    # Rollback - delete the production
                    self.object.delete()
                    return redirect('inventory:production_list')
                    
            else:
                # Just creating production without starting
                self.object.save()
                batch_formset.instance = self.object
                batch_formset.save()
                messages.success(self.request, f'Production {self.object.production_number} created successfully!')
            
            return redirect('inventory:production_list')
        else:
            return self.form_invalid(form)

class ProductionDetailView(DetailView):
    model = Production
    template_name = 'inventory/production_detail.html'
    context_object_name = 'production'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Add material sufficiency checks
        context['sufficiency_checks'] = self.object.sufficiency_checks.all()
        # Add unused material returns
        context['unused_returns'] = self.object.unused_returns.all()
        # Add finished goods created from this production
        context['finished_goods'] = self.object.finished_goods.all()
        return context

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        action = request.POST.get('action')
        
        if action == 'check_materials':
            result = self.object.check_material_sufficiency()
            if result['sufficient']:
                messages.success(request, 'All materials are sufficient.')
            else:
                messages.warning(request, 'Some materials are insufficient.')
                
        elif action == 'start_production':
            success, message = self.object.start_production()
            if success:
                messages.success(request, message)
            else:
                messages.error(request, message)
                
        elif action == 'complete_production':
            success, message = self.object.complete_production()
            if success:
                messages.success(request, message)
            else:
                messages.error(request, message)
                
        elif action == 'cancel_production':
            success, message = self.object.cancel_production(
                employee=request.user.employee if hasattr(request.user, 'employee') else None
            )
            if success:
                messages.success(request, message)
            else:
                messages.error(request, message)
        
        return redirect('inventory:production_detail', pk=self.object.pk)

class ProductionDetailCreateView(CreateView):
    model = ProductionDetail
    form_class = ProductionDetailForm
    template_name = 'inventory/production_detail_form.html'
    success_url = reverse_lazy('inventory:production_list')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        production = get_object_or_404(Production, pk=self.kwargs['pk'])
        context['production'] = production
        return context

    def form_valid(self, form):
        production = get_object_or_404(Production, pk=self.kwargs['pk'])
        form.instance.production = production
        
        # Deduct from stock using FEFO
        success = RawMaterialMovement.deduct_stock_fifo(
            raw_material=form.cleaned_data['raw_material'],
            quantity_to_deduct=form.cleaned_data['quantity_used'],
            unit=form.cleaned_data['unit'],
            reference=f'Production #{production.production_number}',
            notes=f'Used in production of {production.product.name}'
        )
        
        if not success:
            form.add_error(None, 'Not enough stock available for this material.')
            return self.form_invalid(form)
        
        return super().form_valid(form)

@login_required
def product_api_detail(request, pk):
    product = get_object_or_404(Product, pk=pk)
    recipe = ProductRecipe.objects.filter(product=product, is_active=True).first()
    
    data = {
        'id': product.id,
        'name': product.name,
        'recipe': None
    }
    
    if recipe:
        data['recipe'] = {
            'id': recipe.id,
            'recipe_number': recipe.recipe_number,
            'details': [
                {
                    'material_id': detail.material.id,
                    'material_name': detail.material.name,
                    'quantity': str(detail.quantity),
                    'unit': detail.unit
                }
                for detail in recipe.details.all()
            ]
        }
    
    return JsonResponse(data)

@method_decorator(csrf_exempt, name='dispatch')
def ajax_check_materials(request):
    if request.method == 'POST':
        data = json.loads(request.body)
        product_batches = data.get('batches', [])
        material_requirements = {}
        for batch in product_batches:
            product_id = batch['product']
            quantity = Decimal(str(batch['quantity']))
            recipe = ProductRecipe.objects.filter(product_id=product_id, is_active=True).first()
            if recipe:
                for detail in recipe.details.all():
                    mat_id = detail.material.id
                    req_qty = detail.quantity * quantity
                    if mat_id not in material_requirements:
                        material_requirements[mat_id] = {'material': detail.material.name, 'required': Decimal('0'), 'unit': detail.unit}
                    material_requirements[mat_id]['required'] += req_qty
        # Check stock
        for mat_id, req in material_requirements.items():
            material = RawMaterial.objects.get(id=mat_id)
            current_stock = RawMaterialMovement.get_available_stock(material)
            req['current_stock'] = current_stock
            req['sufficient'] = current_stock >= req['required']
        return JsonResponse({'materials': list(material_requirements.values())})
    return JsonResponse({'error': 'Invalid request'}, status=400)

@login_required
def ajax_production_details(request, pk):
    production = get_object_or_404(Production, pk=pk)
    
    # Get related data for the template
    context = {
        'production': production,
        'sufficiency_checks': production.sufficiency_checks.all(),
        'unused_returns': production.unused_returns.all(),
        'finished_goods': production.finished_goods.all()
    }
    
    html = render_to_string('inventory/production_details_modal.html', context, request=request)
    return JsonResponse({'html': html})

@csrf_exempt
@login_required
def ajax_check_material_sufficiency(request, pk):
    """AJAX endpoint to check material sufficiency for a production"""
    if request.method == 'POST':
        production = get_object_or_404(Production, pk=pk)
        result = production.check_material_sufficiency()
        
        # Prepare data for response
        checks_data = []
        for check in result['checks']:
            checks_data.append({
                'material_name': check.raw_material.name,
                'required_quantity': float(check.required_quantity),
                'available_quantity': float(check.available_quantity),
                'is_sufficient': check.is_sufficient,
                'unit': check.unit
            })
        
        return JsonResponse({
            'sufficient': result['sufficient'],
            'message': result['message'],
            'checks': checks_data
        })
    
    return JsonResponse({'error': 'Invalid request'}, status=400)

@csrf_exempt
@login_required
def ajax_start_production(request, pk):
    """AJAX endpoint to start production"""
    if request.method == 'POST':
        production = get_object_or_404(Production, pk=pk)
        success, message = production.start_production()
        
        return JsonResponse({
            'success': success,
            'message': message,
            'status': production.status
        })
    
    return JsonResponse({'error': 'Invalid request'}, status=400)

@csrf_exempt
@login_required  
def ajax_complete_production(request, pk):
    """AJAX endpoint to complete production"""
    if request.method == 'POST':
        production = get_object_or_404(Production, pk=pk)
        success, message = production.complete_production()
        
        return JsonResponse({
            'success': success,
            'message': message,
            'status': production.status
        })
    
    return JsonResponse({'error': 'Invalid request'}, status=400)

@csrf_exempt
@login_required
def ajax_cancel_production(request, pk):
    """AJAX endpoint to cancel production with unused material returns"""
    if request.method == 'POST':
        production = get_object_or_404(Production, pk=pk)
        
        # Parse unused materials data from request
        data = json.loads(request.body.decode('utf-8'))
        unused_materials = data.get('unused_materials', [])
        cancellation_reason = data.get('cancellation_reason', '')
        return_notes = data.get('return_notes', '')
        
        # Get current user's employee record
        employee = None
        if hasattr(request.user, 'employee'):
            employee = request.user.employee
        
        success, message = production.cancel_production(
            unused_materials_data=unused_materials,
            employee=employee,
            cancellation_reason=cancellation_reason,
            return_notes=return_notes
        )
        
        return JsonResponse({
            'success': success,
            'message': message,
            'status': production.status
        })
    
    return JsonResponse({'error': 'Invalid request'}, status=400)

@login_required
def ajax_get_production_materials(request, pk):
    """Get materials used in production for unused material return form"""
    production = get_object_or_404(Production, pk=pk)
    materials_dict = {}
    
    # Group materials by ID and sum quantities (keep original units)
    for detail in production.details.all():
        material_id = detail.raw_material.id
        
        if material_id not in materials_dict:
            materials_dict[material_id] = {
                'id': material_id,
                'name': detail.raw_material.name,
                'brand': detail.raw_material.brand or '',
                'quantity_used': float(detail.quantity_used),  # Keep original quantity and unit
                'unit': detail.unit  # Use the unit as it was used in production
            }
        else:
            # Add to existing material (same unit should be used)
            materials_dict[material_id]['quantity_used'] += float(detail.quantity_used)
    
    # Convert dictionary to list
    materials = list(materials_dict.values())
    
    return JsonResponse({
        'success': True,
        'materials': materials
    })

@login_required
def finished_goods_inventory_list(request):
    """View for finished goods inventory"""
    inventory = FinishedGoodsInventory.objects.filter(
        status='available',
        remaining_quantity__gt=0
    ).order_by('expiry_date', 'production_date')  # Ordered by expiry date
    
    # Calculate three days ahead for template use
    three_days_ahead = get_current_date() + timedelta(days=3)
    
    # Check for expired goods that need attention
    today = get_current_date()
    expired_count = FinishedGoodsInventory.objects.filter(
        expiry_date__lt=today,
        status='available',
        remaining_quantity__gt=0
    ).count()
    
    return render(request, 'inventory/finished_goods_inventory_list.html', {
        'inventory': inventory,
        'three_days_ahead': three_days_ahead,
        'expired_count': expired_count,
    })

@login_required
@csrf_exempt
def ajax_expire_goods(request):
    """AJAX endpoint to manually expire goods and write them off"""
    if request.method == 'POST':
        try:
            # Check for expired goods and write them off
            expired_batches = FinishedGoodsInventory.check_and_expire_goods()
            
            if expired_batches:
                total_loss = sum(item['loss_value'] for item in expired_batches)
                batch_numbers = [item['batch'].batch_number for item in expired_batches]
                
                return JsonResponse({
                    'success': True,
                    'message': f'Successfully wrote off {len(expired_batches)} expired batches worth ₱{total_loss:.2f}',
                    'expired_count': len(expired_batches),
                    'total_loss': float(total_loss),
                    'batches': batch_numbers
                })
            else:
                return JsonResponse({
                    'success': True,
                    'message': 'No expired goods found to write off',
                    'expired_count': 0,
                    'total_loss': 0,
                    'batches': []
                })
                
        except Exception as e:
            return JsonResponse({
                'success': False,
                'message': f'Error processing expired goods: {str(e)}'
            })
    
    return JsonResponse({'error': 'Invalid request'}, status=400)

class ProductionUpdateView(UpdateView):
    model = Production
    form_class = ProductionForm
    template_name = 'inventory/production_form.html'
    success_url = reverse_lazy('inventory:production_list')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if self.request.POST:
            context['batch_formset'] = ProductionBatchProductFormSet(self.request.POST, instance=self.object, prefix='batch_products')
        else:
            context['batch_formset'] = ProductionBatchProductFormSet(instance=self.object, prefix='batch_products')
        
        # Add products for batch dropdown
        context['products'] = Product.objects.filter(is_active=True).order_by('name')
        
        return context

    def form_valid(self, form):
        context = self.get_context_data()
        batch_formset = context['batch_formset']
        
        if not form.instance.can_edit():
            messages.error(self.request, 'Cannot edit production in current status.')
            return self.form_invalid(form)
            
        if batch_formset.is_valid():
            self.object = form.save(commit=False)
            
            # Only allow editing basic details for in-progress productions
            # Status and dates are managed through separate complete/cancel actions
            self.object.save()
            batch_formset.instance = self.object
            batch_formset.save()
            
            messages.success(self.request, f'Production {self.object.production_number} updated successfully!')
            return redirect(self.success_url)
        else:
            return self.form_invalid(form)

class ProductionDeleteView(LoginRequiredMixin, DeleteView):
    model = Production
    template_name = 'inventory/production_confirm_delete.html'
    success_url = reverse_lazy('inventory:production_list')
    
    def post(self, request, *args, **kwargs):
        """Handle AJAX delete requests"""
        if request.headers.get('Content-Type') == 'application/json':
            # AJAX request - handle deletion and return JSON response
            production = self.get_object()
            
            if production.status in ['completed']:
                return JsonResponse({
                    'success': False,
                    'message': 'Cannot delete completed production.'
                })
            
            production_number = production.production_number
            
            try:
                production.delete()
                return JsonResponse({
                    'success': True,
                    'message': f'Production {production_number} deleted successfully.'
                })
            except Exception as e:
                return JsonResponse({
                    'success': False,
                    'message': f'Error deleting production: {str(e)}'
                })
        else:
            # Regular form POST - use the original delete method
            return self.delete(request, *args, **kwargs)
    
    def delete(self, request, *args, **kwargs):
        production = self.get_object()
        if production.status in ['completed']:
            messages.error(request, 'Cannot delete completed production.')
            return redirect('inventory:production_list')
        
        production_number = production.production_number
        result = super().delete(request, *args, **kwargs)
        messages.success(request, f'Production {production_number} deleted successfully.')
        return result

@login_required
@csrf_exempt
def complete_production_view(request, pk):
    """Complete a production and move to finished goods"""
    if request.method == 'POST':
        production = get_object_or_404(Production, pk=pk)
        
        if production.status != 'in_progress':
            return JsonResponse({
                'success': False,
                'message': 'Production must be in progress to complete.'
            })
        
        success, message = production.complete_production()
        return JsonResponse({
            'success': success,
            'message': message
        })
    
    return JsonResponse({'success': False, 'message': 'Invalid request method.'})

@login_required
@csrf_exempt
def cancel_production_view(request, pk):
    """Cancel a production with optional material return handling"""
    if request.method == 'POST':
        production = get_object_or_404(Production, pk=pk)
        
        if production.status in ['completed', 'cancelled']:
            return JsonResponse({
                'success': False,
                'message': 'Cannot cancel completed or already cancelled production.'
            })
        
        # Parse unused materials data if provided
        data = json.loads(request.body.decode('utf-8'))
        unused_materials = data.get('unused_materials', [])
        
        # Get employee
        employee = None
        if hasattr(request.user, 'employee'):
            employee = request.user.employee
        
        success, message = production.cancel_production(
            unused_materials_data=unused_materials,
            employee=employee
        )
        
        return JsonResponse({
            'success': success,
            'message': message
        })
    
    return JsonResponse({'success': False, 'message': 'Invalid request method.'})

@login_required
def ajax_product_recipes(request, pk):
    """Get all recipes for a specific product"""
    product = get_object_or_404(Product, pk=pk)
    recipes = product.recipes.filter(is_active=True).values(
        'id', 'recipe_number', 'description', 'is_active'
    )
    return JsonResponse({'recipes': list(recipes)})

@csrf_exempt
@login_required
def ajax_check_single_product_materials(request):
    """AJAX endpoint to check materials for a single product"""
    if request.method == 'POST':
        data = json.loads(request.body.decode('utf-8'))
        product_id = data.get('product_id')
        quantity = data.get('quantity', 1)
        
        try:
            quantity = Decimal(str(quantity))
            product = Product.objects.get(id=product_id)
            recipe = ProductRecipe.objects.filter(product=product, is_active=True).first()
            
            if not recipe:
                return JsonResponse({
                    'sufficient': False,
                    'message': f'No active recipe found for {product.name}',
                    'materials': []
                })
            
            # Check materials for this product
            insufficient_materials = []
            all_materials = []
            all_sufficient = True
            
            for detail in recipe.details.all():
                required_qty = detail.quantity * quantity
                available_stock = RawMaterialMovement.get_available_stock(detail.material)
                is_sufficient = available_stock >= required_qty
                
                # Add to all materials list
                all_materials.append({
                    'material_name': detail.material.name,
                    'brand': detail.material.brand or '',
                    'required': float(required_qty),
                    'available': float(available_stock),
                    'unit': detail.unit,
                    'is_sufficient': is_sufficient
                })
                
                if not is_sufficient:
                    all_sufficient = False
                    insufficient_materials.append({
                        'material_name': detail.material.name,
                        'brand': detail.material.brand or '',
                        'required': float(required_qty),
                        'available': float(available_stock),
                        'unit': detail.unit,
                        'shortage': float(required_qty - available_stock)
                    })
            
            return JsonResponse({
                'sufficient': all_sufficient,
                'message': 'All materials are sufficient' if all_sufficient else 'Some materials are insufficient',
                'materials': insufficient_materials,
                'all_materials': all_materials,  # New field for complete materials list
                'product_name': product.name
            })
            
        except (Product.DoesNotExist, ValueError, InvalidOperation) as e:
            return JsonResponse({
                'sufficient': False,
                'message': f'Error: {str(e)}',
                'materials': []
            })
    
    return JsonResponse({'error': 'Invalid request'}, status=400)

@csrf_exempt
@login_required
def ajax_check_batch_materials(request):
    """AJAX endpoint to check materials for batch production"""
    if request.method == 'POST':
        data = json.loads(request.body.decode('utf-8'))
        batch_products = data.get('batch_products', [])
        
        # Calculate total required for each material across all products
        material_requirements = {}
        product_names = []
        
        for batch_item in batch_products:
            product_id = batch_item.get('product_id')
            quantity = batch_item.get('quantity', 1)
            
            try:
                quantity = Decimal(str(quantity))
                product = Product.objects.get(id=product_id)
                product_names.append(product.name)
                recipe = ProductRecipe.objects.filter(product=product, is_active=True).first()
                
                if recipe:
                    for detail in recipe.details.all():
                        mat_id = detail.material.id
                        req_qty = detail.quantity * quantity
                        
                        if mat_id not in material_requirements:
                            material_requirements[mat_id] = {
                                'material_name': detail.material.name,
                                'brand': detail.material.brand or '',
                                'required': Decimal('0'),
                                'unit': detail.unit
                            }
                        material_requirements[mat_id]['required'] += req_qty
                        
            except (Product.DoesNotExist, ValueError, InvalidOperation):
                continue
        
        # Check stock for all materials
        insufficient_materials = []
        all_materials = []
        all_sufficient = True
        
        for mat_id, req_data in material_requirements.items():
            try:
                material = RawMaterial.objects.get(id=mat_id)
                available_stock = RawMaterialMovement.get_available_stock(material)
                required_qty = req_data['required']
                is_sufficient = available_stock >= required_qty
                
                # Add to all materials list for View Materials modal
                all_materials.append({
                    'material_name': req_data['material_name'],
                    'brand': req_data['brand'],
                    'required': float(required_qty),
                    'available': float(available_stock),
                    'unit': req_data['unit'],
                    'is_sufficient': is_sufficient
                })
                
                if not is_sufficient:
                    all_sufficient = False
                    insufficient_materials.append({
                        'material_name': req_data['material_name'],
                        'brand': req_data['brand'],
                        'required': float(required_qty),
                        'available': float(available_stock),
                        'unit': req_data['unit'],
                        'shortage': float(required_qty - available_stock)
                    })
                    
            except RawMaterial.DoesNotExist:
                continue
        
        return JsonResponse({
            'sufficient': all_sufficient,
            'message': 'All materials are sufficient' if all_sufficient else 'Some materials are insufficient',
            'materials': insufficient_materials,
            'all_materials': all_materials,  # New field for View Materials modal
            'products': product_names
        })
    
    return JsonResponse({'error': 'Invalid request'}, status=400)

@csrf_exempt
@login_required
def ajax_check_single_product_materials_with_allocations(request):
    """AJAX endpoint to check materials for a single product considering other allocations"""
    if request.method == 'POST':
        data = json.loads(request.body.decode('utf-8'))
        product_id = data.get('product_id')
        quantity = data.get('quantity', 1)
        other_allocations = data.get('other_allocations', [])
        
        try:
            quantity = Decimal(str(quantity))
            product = Product.objects.get(id=product_id)
            recipe = ProductRecipe.objects.filter(product=product, is_active=True).first()
            
            if not recipe:
                return JsonResponse({
                    'sufficient': False,
                    'message': f'No active recipe found for {product.name}',
                    'materials': []
                })
            
            # Calculate material allocations from other products
            allocated_materials = {}
            for allocation in other_allocations:
                other_product_id = allocation.get('product_id')
                other_quantity = Decimal(str(allocation.get('quantity', 0)))
                
                try:
                    other_product = Product.objects.get(id=other_product_id)
                    other_recipe = ProductRecipe.objects.filter(product=other_product, is_active=True).first()
                    
                    if other_recipe:
                        for detail in other_recipe.details.all():
                            material_id = detail.material.id
                            required_qty = detail.quantity * other_quantity
                            
                            if material_id not in allocated_materials:
                                allocated_materials[material_id] = Decimal('0')
                            allocated_materials[material_id] += required_qty
                            
                except (Product.DoesNotExist, ValueError, InvalidOperation):
                    continue
            
            # Check materials for this product with reduced availability
            insufficient_materials = []
            all_materials = []
            all_sufficient = True
            
            for detail in recipe.details.all():
                required_qty = detail.quantity * quantity
                total_available_stock = RawMaterialMovement.get_available_stock(detail.material)
                
                # Reduce available stock by what's already allocated to other products
                allocated_qty = allocated_materials.get(detail.material.id, Decimal('0'))
                available_after_allocation = total_available_stock - allocated_qty
                
                is_sufficient = available_after_allocation >= required_qty
                
                # Add to all materials list
                all_materials.append({
                    'material_name': detail.material.name,
                    'brand': detail.material.brand or '',
                    'required': float(required_qty),
                    'available': float(available_after_allocation),
                    'total_stock': float(total_available_stock),  # For debugging/info
                    'allocated_to_others': float(allocated_qty),  # For debugging/info
                    'unit': detail.unit,
                    'is_sufficient': is_sufficient
                })
                
                if not is_sufficient:
                    all_sufficient = False
                    insufficient_materials.append({
                        'material_name': detail.material.name,
                        'brand': detail.material.brand or '',
                        'required': float(required_qty),
                        'available': float(available_after_allocation),
                        'unit': detail.unit,
                        'shortage': float(required_qty - available_after_allocation)
                    })
            
            return JsonResponse({
                'sufficient': all_sufficient,
                'message': 'All materials are sufficient' if all_sufficient else 'Some materials are insufficient',
                'materials': insufficient_materials,
                'all_materials': all_materials,
                'product_name': product.name
            })
            
        except (Product.DoesNotExist, ValueError, InvalidOperation) as e:
            return JsonResponse({
                'sufficient': False,
                'message': f'Error: {str(e)}',
                'materials': []
            })
    
    return JsonResponse({'error': 'Invalid request'}, status=400) 