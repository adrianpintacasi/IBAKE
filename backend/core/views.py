from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import TemplateView
from django.http import HttpResponse
from inventory.models import RawMaterial, FinishedGood, StockMovement, RawMaterialMovement, Production, FinishedGoodsInventory, Product
from accounting.models import JournalEntry, PayrollEntry, UtilityEntry
from django.db import models
from django.utils import timezone
from datetime import timedelta
import csv
from decimal import Decimal

class DashboardView(LoginRequiredMixin, TemplateView):
    template_name = 'core/dashboard.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # === RAW MATERIALS INVENTORY ===
        # Movement Statistics
        context['movement_stats'] = {
            'in_count': RawMaterialMovement.objects.filter(movement_type='IN').count(),
            'out_count': RawMaterialMovement.objects.filter(movement_type='OUT').count(),
            'adj_count': RawMaterialMovement.objects.filter(movement_type='ADJ').count(),
            'total_count': RawMaterialMovement.objects.count(),
        }
        
        # Low Stock Materials (materials below minimum stock level)
        # NOTE: Using same logic as inventory status view for consistency
        # This compares available_stock (base units) with minimum_stock (original units)
        # which is technically incorrect but matches the existing inventory status behavior
        low_stock_materials = []
        out_of_stock_materials = []
        for material in RawMaterial.objects.filter(is_active=True):
            available_stock = RawMaterialMovement.get_available_stock(material)
            
            # Use same logic as inventory status view (comparing base units with original units)
            if available_stock <= material.minimum_stock:
                material_data = {
                    'material': material,
                    'available_stock': available_stock,
                    'minimum_stock': material.minimum_stock,  # Keep original for display
                    'minimum_stock_base': material.minimum_stock,  # Use same value for template consistency
                    'status': 'critical' if available_stock == 0 else 'low',
                    'shortage': max(0, material.minimum_stock - available_stock)
                }
                if available_stock == 0:
                    out_of_stock_materials.append(material_data)
                else:
                    low_stock_materials.append(material_data)
        
        # Sort by severity (critical first, then by shortage amount)
        low_stock_materials.sort(key=lambda x: x['shortage'], reverse=True)
        out_of_stock_materials.sort(key=lambda x: x['material'].name)
        
        # Combine for dashboard display (all items, not limited to 5)
        all_critical_materials = out_of_stock_materials + low_stock_materials
        context['low_stock_materials'] = all_critical_materials[:5]  # Keep 5 for dashboard card
        context['all_low_stock_materials'] = all_critical_materials  # All for detailed view
        context['out_of_stock_count'] = len(out_of_stock_materials)
        context['low_stock_count'] = len(low_stock_materials)
        
        # Stock Value Summary
        total_stock_value = 0
        materials_with_stock = []
        for material in RawMaterial.objects.filter(is_active=True):
            available_stock = RawMaterialMovement.get_available_stock(material)
            if available_stock > 0:
                # Convert available_stock from base units to stock-in units for proper valuation
                stock_in_units = material.from_base_unit(available_stock)
                value = stock_in_units * material.unit_cost
                total_stock_value += value
                materials_with_stock.append({
                    'material': material,
                    'available_stock': available_stock,
                    'value': value
                })
        
        context['total_stock_value'] = total_stock_value
        context['materials_with_stock_count'] = len(materials_with_stock)
        
        # Recent Activity
        context['recent_stock_movements'] = RawMaterialMovement.objects.select_related('raw_material').order_by('-date')[:5]
        
        # === FINISHED GOODS INVENTORY ===
        # Finished Goods Statistics
        available_finished_goods = FinishedGoodsInventory.objects.filter(
            status='available',
            remaining_quantity__gt=0
        )
        
        context['finished_goods_stats'] = {
            'total_batches': available_finished_goods.count(),
            'total_products': available_finished_goods.values('product').distinct().count(),
            'total_quantity': available_finished_goods.aggregate(
                total=models.Sum('remaining_quantity')
            )['total'] or 0,
        }
        
        # Expiring Soon (next 3 days)
        three_days_ahead = timezone.now().date() + timedelta(days=3)
        seven_days_ahead = timezone.now().date() + timedelta(days=7)
        
        expiring_soon = FinishedGoodsInventory.objects.filter(
            status='available',
            remaining_quantity__gt=0,
            expiry_date__lte=three_days_ahead
        ).order_by('expiry_date')
        
        expiring_week = FinishedGoodsInventory.objects.filter(
            status='available',
            remaining_quantity__gt=0,
            expiry_date__lte=seven_days_ahead,
            expiry_date__gt=three_days_ahead
        ).order_by('expiry_date')
        
        context['expiring_finished_goods'] = expiring_soon[:5]  # Keep 5 for dashboard card
        context['all_expiring_soon'] = expiring_soon  # All expiring in 3 days
        context['expiring_week'] = expiring_week  # Expiring in 4-7 days
        context['expiring_count'] = expiring_soon.count()
        context['expiring_week_count'] = expiring_week.count()
        context['three_days_ahead'] = three_days_ahead
        context['seven_days_ahead'] = seven_days_ahead
        
        # Finished Goods Value
        finished_goods_value = 0
        for item in available_finished_goods:
            finished_goods_value += item.remaining_quantity * item.product.selling_price
        context['finished_goods_value'] = finished_goods_value
        
        # Recent Finished Goods Activity
        context['recent_finished_goods'] = FinishedGoodsInventory.objects.select_related('product', 'production').order_by('-created_at')[:5]
        
        # === PRODUCTION ACTIVITY ===
        # Production Activity (last 7 days)
        week_ago = timezone.now().date() - timedelta(days=7)
        context['recent_productions'] = Production.objects.filter(
            created_at__date__gte=week_ago
        ).order_by('-created_at')[:5]
        
        # Quick Stats
        context['total_materials'] = RawMaterial.objects.filter(is_active=True).count()
        context['active_productions'] = Production.objects.filter(status='in_progress').count()
        context['total_products'] = Product.objects.filter(is_active=True).count()
        
        # === LEGACY STOCK MOVEMENTS (for compatibility) ===
        context['recent_movements'] = StockMovement.objects.all().order_by('-created_at')[:5]
        
        # === ACCOUNTING DATA ===
        context['recent_journals'] = JournalEntry.objects.all().order_by('-date', '-id')[:5]  # Latest first
        
        # Add key accounting metrics to the main dashboard
        from accounting.utils import (
            calculate_cash_balance, calculate_accounts_receivable,
            calculate_raw_materials_inventory, calculate_finished_goods_inventory,
            calculate_sales_revenue
        )
        
        context['accounting_metrics'] = {
            'cash_balance': calculate_cash_balance(),
            'accounts_receivable': calculate_accounts_receivable(),
            'inventory_value': calculate_raw_materials_inventory() + calculate_finished_goods_inventory(),
            'sales_revenue': calculate_sales_revenue(),
        }
        
        # Recent accounting activity
        context['recent_payroll'] = PayrollEntry.objects.all().order_by('-payment_date')[:3]
        context['recent_utilities'] = UtilityEntry.objects.all().order_by('-payment_date')[:3]
        
        today = timezone.now().date()
        try:
            from sales_management.models import SalesOrder
            
            today_sales = SalesOrder.objects.filter(
                order_date__date=today
            ).aggregate(
                total=models.Sum('total_amount')
            )['total'] or Decimal('0')
            
            # Total revenue (all time sales)
            total_revenue = SalesOrder.objects.aggregate(
                total=models.Sum('total_amount')
            )['total'] or Decimal('0')
            
            context['today_sales'] = today_sales
            context['total_revenue'] = total_revenue
            
        except ImportError:
            # Sales management module not available
            context['today_sales'] = 0
            context['total_revenue'] = 0
        
        return context

class HomeView(TemplateView):
    template_name = 'core/home.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if self.request.user.is_authenticated:
            context['dashboard_url'] = 'dashboard'
        return context 

@login_required
def export_grocery_list(request):
    """Export low stock and out of stock materials as CSV for grocery shopping"""
    
    # Get all low stock and out of stock materials
    # Using same logic as inventory status view for consistency
    low_stock_materials = []
    out_of_stock_materials = []
    
    for material in RawMaterial.objects.filter(is_active=True):
        available_stock = RawMaterialMovement.get_available_stock(material)
        
        # Use same logic as inventory status view (comparing base units with original units)
        if available_stock <= material.minimum_stock:
            shortage = max(0, material.minimum_stock - available_stock)
            
            material_data = {
                'material': material,
                'available_stock': available_stock,
                'minimum_stock': material.minimum_stock,  # Use original units
                'shortage': shortage,
                'status': 'OUT OF STOCK' if available_stock == 0 else 'LOW STOCK'
            }
            
            if available_stock == 0:
                out_of_stock_materials.append(material_data)
            else:
                low_stock_materials.append(material_data)
    
    # Combine all materials for the general export
    all_materials = out_of_stock_materials + low_stock_materials
    
    # Sort by priority (out of stock first, then by shortage)
    all_materials.sort(key=lambda x: (x['available_stock'] > 0, -x['shortage']))
    
    # Create CSV response
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="grocery_list_{timezone.now().strftime("%Y%m%d_%H%M")}.csv"'
    
    writer = csv.writer(response)
    
    # Write header with date and title
    writer.writerow([f'Low Stock and Out of Stock Materials - {timezone.now().strftime("%Y-%m-%d %H:%M:%S")}'])
    writer.writerow([])  # Empty row
    
    # Write column headers
    writer.writerow([
        'Material Name',
        'Brand',
        'Current Stock',
        'Minimum Required',
        'Shortage'
    ])
    
    # Write data rows
    for item in all_materials:
        material = item['material']
        
        writer.writerow([
            material.name,
            material.brand or '',
            f"{item['available_stock']:.2f}",
            f"{item['minimum_stock']:.2f}",
            f"{item['shortage']:.2f}"
        ])
    
    return response

@login_required
def export_out_of_stock(request):
    """Export only out of stock materials as CSV"""
    
    out_of_stock_materials = []
    
    for material in RawMaterial.objects.filter(is_active=True):
        available_stock = RawMaterialMovement.get_available_stock(material)
        
        if available_stock == 0:
            shortage = material.minimum_stock  # Full minimum stock is needed
            
            out_of_stock_materials.append({
                'material': material,
                'available_stock': available_stock,
                'minimum_stock': material.minimum_stock,
                'shortage': shortage
            })
    
    # Sort by material name
    out_of_stock_materials.sort(key=lambda x: x['material'].name)
    
    # Create CSV response
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="out_of_stock_materials_{timezone.now().strftime("%Y%m%d_%H%M")}.csv"'
    
    writer = csv.writer(response)
    
    # Write header with date and title
    writer.writerow([f'Out of Stock Materials - {timezone.now().strftime("%Y-%m-%d %H:%M:%S")}'])
    writer.writerow([])  # Empty row
    
    # Write column headers
    writer.writerow([
        'Material Name',
        'Brand',
        'Current Stock',
        'Minimum Required',
        'Shortage'
    ])
    
    # Write data rows
    for item in out_of_stock_materials:
        material = item['material']
        
        writer.writerow([
            material.name,
            material.brand or '',
            f"{item['available_stock']:.2f}",
            f"{item['minimum_stock']:.2f}",
            f"{item['shortage']:.2f}"
        ])
    
    return response

@login_required
def export_low_stock(request):
    """Export only low stock materials as CSV"""
    
    low_stock_materials = []
    
    for material in RawMaterial.objects.filter(is_active=True):
        available_stock = RawMaterialMovement.get_available_stock(material)
        
        if 0 < available_stock <= material.minimum_stock:
            shortage = material.minimum_stock - available_stock
            
            low_stock_materials.append({
                'material': material,
                'available_stock': available_stock,
                'minimum_stock': material.minimum_stock,
                'shortage': shortage
            })
    
    # Sort by shortage (highest first)
    low_stock_materials.sort(key=lambda x: -x['shortage'])
    
    # Create CSV response
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="low_stock_materials_{timezone.now().strftime("%Y%m%d_%H%M")}.csv"'
    
    writer = csv.writer(response)
    
    # Write header with date and title
    writer.writerow([f'Low Stock Materials - {timezone.now().strftime("%Y-%m-%d %H:%M:%S")}'])
    writer.writerow([])  # Empty row
    
    # Write column headers
    writer.writerow([
        'Material Name',
        'Brand',
        'Current Stock',
        'Minimum Required',
        'Shortage'
    ])
    
    # Write data rows
    for item in low_stock_materials:
        material = item['material']
        
        writer.writerow([
            material.name,
            material.brand or '',
            f"{item['available_stock']:.2f}",
            f"{item['minimum_stock']:.2f}",
            f"{item['shortage']:.2f}"
        ])
    
    return response 