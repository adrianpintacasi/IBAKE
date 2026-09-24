from django.contrib import admin
from .models import (RawMaterial, FinishedGood, Product, ProductRecipe, ProductRecipeDetail, 
                     StockIn, StockInDetail, StockMovement, Production, ProductionDetail, 
                     RawMaterialMovement, ProductionBatchProduct, FinishedGoodsInventory,
                     MaterialSufficiencyCheck, UnusedMaterialReturn)

@admin.register(RawMaterial)
class RawMaterialAdmin(admin.ModelAdmin):
    list_display = ['code', 'name', 'category', 'unit', 'minimum_stock', 'is_active']
    list_filter = ['category', 'is_active']
    search_fields = ['code', 'name', 'brand']

@admin.register(FinishedGood)
class FinishedGoodAdmin(admin.ModelAdmin):
    list_display = ['code', 'name', 'category', 'unit', 'minimum_stock', 'is_active']
    list_filter = ['category', 'is_active']
    search_fields = ['code', 'name']

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ['name', 'category', 'base_price', 'selling_price', 'is_active']
    list_filter = ['category', 'is_active']
    search_fields = ['name']

@admin.register(ProductRecipe)
class ProductRecipeAdmin(admin.ModelAdmin):
    list_display = ['recipe_number', 'product', 'employee', 'is_active', 'created_at']
    list_filter = ['is_active', 'created_at']
    search_fields = ['recipe_number', 'product__name']

@admin.register(FinishedGoodsInventory)
class FinishedGoodsInventoryAdmin(admin.ModelAdmin):
    list_display = ['batch_number', 'product', 'quantity', 'remaining_quantity', 'production_date', 'expiry_date', 'status']
    list_filter = ['status', 'production_date', 'expiry_date']
    search_fields = ['batch_number', 'product__name']
    readonly_fields = ['batch_number']
    ordering = ['expiry_date', 'production_date']  # FEFO ordering

@admin.register(RawMaterialMovement)
class RawMaterialMovementAdmin(admin.ModelAdmin):
    list_display = ['movement_number', 'date', 'movement_type', 'raw_material', 'quantity', 'remaining_quantity', 'unit', 'reference']
    list_filter = ['movement_type', 'date', 'raw_material']
    search_fields = ['movement_number', 'raw_material__name', 'reference']
    readonly_fields = ['movement_number', 'remaining_quantity']  # Don't allow manual editing of these fields
    ordering = ['-date', '-movement_number']
    
    def get_list_display(self, request):
        """Customize list display based on movement type"""
        list_display = list(self.list_display)
        return list_display

# Register remaining models
admin.site.register(StockIn)
admin.site.register(StockInDetail)
admin.site.register(StockMovement)
admin.site.register(Production)
admin.site.register(ProductionDetail)
admin.site.register(ProductRecipeDetail)
admin.site.register(ProductionBatchProduct) 
admin.site.register(MaterialSufficiencyCheck)
admin.site.register(UnusedMaterialReturn) 