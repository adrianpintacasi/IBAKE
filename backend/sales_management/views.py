from django.shortcuts import render, get_object_or_404, redirect
from django.views.generic import ListView, View
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from .models import SalesOrder, SalesOrderItem
from .forms import SalesOrderForm, SalesOrderItemForm
from inventory.models import Product, FinishedGoodsInventory, RawMaterialMovement, ProductRecipe
from employee.models import Employee
from customer_management.models import Customer
from django.template.loader import render_to_string
from django.views.decorators.csrf import csrf_exempt
from django.db import transaction
from django.contrib import messages
import json
from decimal import Decimal
from accounting.utils import create_journal_entry, calculate_product_cost

@method_decorator(login_required, name='dispatch')
class SalesOrderListView(ListView):
    model = SalesOrder
    template_name = 'sales_management/sales_order_list.html'
    context_object_name = 'orders'
    ordering = ['-order_date']

@method_decorator(login_required, name='dispatch')
class SalesOrderCreateView(View):
    def get(self, request):
        form = SalesOrderForm()
        products = list(Product.objects.filter(is_active=True).values('id', 'name', 'selling_price', 'category'))
        customers = Customer.objects.filter(is_active=True)
        employees = Employee.objects.filter(is_active=True)
        return render(request, 'sales_management/sales_order_form.html', {
            'form': form,
            'item_form': SalesOrderItemForm(),
            'products': products,
            'customers': customers,
            'employees': employees,
        })

    def post(self, request):
        data = request.POST.copy()
        items_json = data.get('items_json')
        
        # Remove items from form data to avoid validation issues
        if 'items_json' in data:
            del data['items_json']
        
        form = SalesOrderForm(data)

        if form.is_valid() and items_json:
            try:
                with transaction.atomic():
                    # Create the sales order
                    order = form.save(commit=False)
                    order.save()
                    
                    items = json.loads(items_json)
                    total = Decimal('0')
                    
                    # Create sales order items first
                    created_items = []
                    for item in items:
                        product = Product.objects.get(pk=item['product'])
                        quantity = int(item['quantity'])
                        unit_price = Decimal(str(item['unit_price']))
                        discount = Decimal(str(item.get('discount', 0)))
                        
                        # Create the sales order item
                        sales_item = SalesOrderItem.objects.create(
                            sales_order=order,
                            product=product,
                            quantity=quantity,
                            unit_price=unit_price,
                            discount=discount
                        )
                        created_items.append(sales_item)
                        
                        # Category-based inventory deduction
                        if product.category.lower() in ['cake', 'pastry', 'dessert']:
                            # Deduct from finished goods inventory using FEFO
                            success = self._deduct_finished_goods(product, quantity, order)
                            if not success:
                                raise Exception(f"Insufficient finished goods inventory for {product.name}")
                        
                        elif product.category.lower() in ['snack', 'coffee', 'non-coffee']:
                            # Deduct raw materials based on recipe (made-to-order)
                            success = self._deduct_raw_materials(product, quantity, order)
                            if not success:
                                raise Exception(f"Insufficient raw materials for {product.name}")
                        
                        subtotal = Decimal(str(quantity)) * unit_price * (Decimal('1') - discount / Decimal('100'))
                        total += subtotal
                    
                    # Update order total
                    order.total_amount = total
                    order.save()
                    
                    # Create automatic journal entries for sales order - CRITICAL SECTION
                    if total > 0:
                        cogs_total = Decimal('0')
                        for sales_item in created_items:
                            product_cost = calculate_product_cost(sales_item.product)
                            cogs_total += Decimal(str(sales_item.quantity)) * product_cost
                        
                        # Create revenue journal entry
                        revenue_transactions = []
                        amount_receivable = total - order.amount_paid
                        
                        if order.amount_paid > 0:
                            # Cash received
                            revenue_transactions.append({
                                'account_code': 'CASH',
                                'debit': order.amount_paid,
                                'credit': Decimal('0'),
                                'description': f'Cash received - Sales Order #{order.sales_order_id}'
                            })
                        
                        if amount_receivable > 0:
                            # Amount still owed
                            revenue_transactions.append({
                                'account_code': 'ACCT_REC',
                                'debit': amount_receivable,
                                'credit': Decimal('0'),
                                'description': f'Amount receivable - Sales Order #{order.sales_order_id}'
                            })
                        
                        # Sales revenue (credit)
                        revenue_transactions.append({
                            'account_code': 'SALES_REV',
                            'debit': Decimal('0'),
                            'credit': total,
                            'description': f'Sales revenue - Sales Order #{order.sales_order_id}'
                        })
                        
                        # Create revenue journal entry - MUST SUCCEED
                        revenue_entry = create_journal_entry(
                                description=f"Sales Order #{order.sales_order_id} - Revenue Recognition",
                                transactions=revenue_transactions,
                                reference_type='sales_order',
                                reference_id=order.sales_order_id,
                                entry_date=order.order_date.date()
                            )
                        
                        # Create COGS journal entry - MUST SUCCEED
                        if cogs_total > 0:
                            cogs_entry = create_journal_entry(
                                    description=f"Sales Order #{order.sales_order_id} - Cost of Goods Sold",
                                    transactions=[
                                        {
                                            'account_code': 'COGS',
                                            'debit': cogs_total,
                                            'credit': Decimal('0'),
                                            'description': f'COGS - Sales Order #{order.sales_order_id}'
                                        },
                                        {
                                            'account_code': 'FIN_GOODS',
                                            'debit': Decimal('0'),
                                            'credit': cogs_total,
                                            'description': f'Finished goods sold - Sales Order #{order.sales_order_id}'
                                        }
                                    ],
                                    reference_type='sales_order',
                                    reference_id=order.sales_order_id,
                                    entry_date=order.order_date.date()
                                )
                        
                        # If we reach here, both journal entries were created successfully
                        messages.success(
                            request, 
                            f'Sales Order #{order.sales_order_id} created successfully with journal entries '
                            f'{revenue_entry.entry_number}' + 
                            (f' and {cogs_entry.entry_number}' if cogs_total > 0 else '')
                        )
                    
                    return redirect('sales_management:sales_order_list')
                    
            except Exception as e:
                # If any error occurs (including journal entry failures), the transaction will be rolled back
                error_msg = f"Error processing sales order: {str(e)}"
                if "journal" in str(e).lower():
                    error_msg += " - Journal entry creation failed. Sales order was not created."
                form.add_error(None, error_msg)
        
        # fallback - show form with errors
        products = list(Product.objects.filter(is_active=True).values('id', 'name', 'selling_price', 'category'))
        customers = Customer.objects.filter(is_active=True)
        employees = Employee.objects.filter(is_active=True)
        return render(request, 'sales_management/sales_order_form.html', {
            'form': form,
            'item_form': SalesOrderItemForm(),
            'products': products,
            'customers': customers,
            'employees': employees,
        })
    
    def _deduct_finished_goods(self, product, quantity, sales_order):
        """
        Deduct finished goods using FEFO (First Expired First Out) method
        """
        try:
            consumed_batches = FinishedGoodsInventory.consume_fefo(
                product=product,
                quantity_to_consume=quantity,
                reference=f'Sales Order #{sales_order.sales_order_id}',
                notes=f'Sold to {sales_order.customer_name}'
            )
            return consumed_batches is not None
        except Exception as e:
            print(f"Error deducting finished goods: {e}")
            return False
    
    def _deduct_raw_materials(self, product, quantity, sales_order):
        """
        Deduct raw materials based on product recipe for made-to-order items
        """
        try:
            # Get the active recipe for this product
            recipe = ProductRecipe.objects.filter(product=product, is_active=True).first()
            if not recipe:
                print(f"No active recipe found for {product.name}")
                return False
            
            # Deduct each ingredient using FIFO method
            for recipe_detail in recipe.details.all():
                required_qty = recipe_detail.quantity * quantity
                
                success = RawMaterialMovement.deduct_stock_fifo(
                    raw_material=recipe_detail.material,
                    quantity_to_deduct=required_qty,
                    unit=recipe_detail.unit,
                    reference=f'Sales Order #{sales_order.sales_order_id} - {product.name}',
                    notes=f'Made-to-order for {sales_order.customer_name}'
                )
                
                if not success:
                    print(f"Insufficient stock for {recipe_detail.material.name}")
                    return False
            
            return True
            
        except Exception as e:
            print(f"Error deducting raw materials: {e}")
            return False

@login_required
@csrf_exempt
def ajax_add_customer(request):
    if request.method == 'POST':
        # Create customer in customer_management app
        customer_data = {
            'first_name': request.POST.get('first_name', '').strip(),
            'last_name': request.POST.get('last_name', '').strip(),
            'phone': request.POST.get('phone', '').strip(),
            'email': request.POST.get('email', '').strip(),
            'address': request.POST.get('address', '').strip(),
            'added_by_id': request.POST.get('added_by'),  # Employee who added this customer
            'is_active': True
        }
        
        # Validate required fields
        if not customer_data['first_name'] or not customer_data['last_name']:
            return JsonResponse({'success': False, 'error': 'First name and last name are required'})
        
        if not customer_data['added_by_id']:
            return JsonResponse({'success': False, 'error': 'Please select an employee'})
        
        try:
            # Validate that the employee exists
            employee = Employee.objects.get(id=customer_data['added_by_id'])
            
            # Create the customer
            customer = Customer.objects.create(**customer_data)
            
            return JsonResponse({
                'success': True, 
                'customer': {
                    'id': customer.id, 
                    'name': f"{customer.first_name} {customer.last_name}",
                    'address': customer.address
                }
            })
        except Employee.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Selected employee does not exist'})
        except Exception as e:
            return JsonResponse({'success': False, 'error': f'Error creating customer: {str(e)}'})
    
    return JsonResponse({'success': False, 'error': 'Invalid request'})

@login_required
def ajax_order_details(request, pk):
    print(f"=== AJAX ORDER DETAILS DEBUG ===")
    print(f"Request method: {request.method}")
    print(f"Order ID: {pk}")
    
    try:
        order = get_object_or_404(SalesOrder, pk=pk)
        print(f"Order found: {order}")
        html = render_to_string('sales_management/sales_order_detail_modal.html', {'order': order})
        print(f"HTML rendered successfully, length: {len(html)}")
        return JsonResponse({'html': html})
    except Exception as e:
        print(f"Error in ajax_order_details: {e}")
        return JsonResponse({'error': str(e)}, status=500)

@login_required
@csrf_exempt
def ajax_order_delete(request, pk):
    print(f"=== AJAX ORDER DELETE DEBUG ===")
    print(f"Request method: {request.method}")
    print(f"Order ID: {pk}")
    
    try:
        order = get_object_or_404(SalesOrder, pk=pk)
        print(f"Order found: {order}")
        
        if request.method == 'POST':
            print("Deleting order...")
            order.delete()
            print("Order deleted successfully")
            return JsonResponse({'success': True})
        
        html = render_to_string('sales_management/delete_confirm_modal.html', {'order': order})
        print(f"HTML rendered successfully, length: {len(html)}")
        return JsonResponse({'html': html})
    except Exception as e:
        print(f"Error in ajax_order_delete: {e}")
        return JsonResponse({'error': str(e)}, status=500)

@login_required
@csrf_exempt
def ajax_add_payment(request):
    print(f"=== AJAX ADD PAYMENT DEBUG ===")
    print(f"Request method: {request.method}")
    
    if request.method == 'POST':
        order_id = request.POST.get('order_id')
        payment_amount = request.POST.get('payment_amount')
        print(f"Order ID: {order_id}")
        print(f"Payment amount (raw): {payment_amount}")
        
        try:
            order = SalesOrder.objects.get(sales_order_id=order_id)
            payment_amount = Decimal(str(payment_amount))
            print(f"Payment amount (Decimal): {payment_amount}")
            print(f"Order balance before: {order.balance}")
            print(f"Order amount_paid before: {order.amount_paid}")
            
            # Validate payment amount
            if payment_amount <= 0:
                return JsonResponse({'success': False, 'error': 'Payment amount must be greater than 0'})
            
            if payment_amount > order.balance:
                return JsonResponse({'success': False, 'error': 'Payment amount cannot exceed balance'})
            
            # Add payment
            new_balance, journal_entry = order.add_payment(payment_amount)
            print(f"Order amount_paid after: {order.amount_paid}")
            print(f"New balance: {new_balance}")
            print(f"Journal entry created: {journal_entry.entry_number if journal_entry else 'None'}")
            print(f"New status: {order.status}")
            
            return JsonResponse({
                'success': True, 
                'new_balance': float(new_balance),
                'new_status': order.status,
                'amount_paid': float(order.amount_paid),
                'journal_entry': journal_entry.entry_number if journal_entry else None
            })
            
        except SalesOrder.DoesNotExist:
            print("Error: Sales order not found")
            return JsonResponse({'success': False, 'error': 'Sales order not found'})
        except (ValueError, TypeError) as e:
            print(f"Error: Invalid payment amount: {e}")
            return JsonResponse({'success': False, 'error': f'Invalid payment amount: {str(e)}'})
        except Exception as e:
            print(f"Error: {e}")
            return JsonResponse({'success': False, 'error': str(e)})
    
    return JsonResponse({'success': False, 'error': 'Invalid request method'})

@login_required
@csrf_exempt
def ajax_check_inventory(request):
    """
    Check inventory availability for sales order items before creating the order
    """
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            items = data.get('items', [])
            
            availability_issues = []
            
            for item in items:
                product_id = item.get('product')
                quantity = int(item.get('quantity', 0))
                
                if not product_id or quantity <= 0:
                    continue
                
                try:
                    product = Product.objects.get(id=product_id)
                    category = product.category.lower()
                    
                    if category in ['cake', 'pastry', 'dessert']:
                        # Check finished goods inventory
                        available_qty = FinishedGoodsInventory.get_available_stock(product)
                        if available_qty < quantity:
                            availability_issues.append({
                                'product': product.name,
                                'category': product.category,
                                'type': 'finished_goods',
                                'requested': quantity,
                                'available': available_qty,
                                'shortage': quantity - available_qty
                            })
                    
                    elif category in ['snack', 'coffee', 'non-coffee']:
                        # Check raw materials based on recipe
                        recipe = ProductRecipe.objects.filter(product=product, is_active=True).first()
                        if not recipe:
                            availability_issues.append({
                                'product': product.name,
                                'category': product.category,
                                'type': 'no_recipe',
                                'message': f'No active recipe found for {product.name}'
                            })
                            continue
                        
                        # Check each ingredient
                        for recipe_detail in recipe.details.all():
                            required_qty = recipe_detail.quantity * quantity
                            available_qty = RawMaterialMovement.get_available_stock(recipe_detail.material)
                            
                            if available_qty < required_qty:
                                availability_issues.append({
                                    'product': product.name,
                                    'category': product.category,
                                    'type': 'raw_material',
                                    'ingredient': recipe_detail.material.name,
                                    'requested': required_qty,
                                    'available': available_qty,
                                    'shortage': required_qty - available_qty,
                                    'unit': recipe_detail.unit
                                })
                
                except Product.DoesNotExist:
                    availability_issues.append({
                        'product': 'Unknown Product',
                        'type': 'invalid_product',
                        'message': f'Product with ID {product_id} not found'
                    })
            
            return JsonResponse({
                'success': True,
                'has_issues': len(availability_issues) > 0,
                'issues': availability_issues
            })
            
        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': f'Error checking inventory: {str(e)}'
            })
    
    return JsonResponse({'success': False, 'error': 'Invalid request method'})
