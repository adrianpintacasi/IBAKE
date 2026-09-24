from django.urls import path
from . import views

app_name = 'inventory'

urlpatterns = [
    path('raw-materials/', views.RawMaterialListView.as_view(), name='raw_material_list'),
    path('raw-materials/add/', views.RawMaterialCreateView.as_view(), name='raw_material_add'),
    path('raw-materials/<int:pk>/edit/', views.RawMaterialUpdateView.as_view(), name='raw_material_edit'),
    path('raw-materials/<int:pk>/delete/', views.RawMaterialDeleteView.as_view(), name='raw_material_delete'),

    path('finished-goods/', views.FinishedGoodListView.as_view(), name='finished_good_list'),
    path('finished-goods/add/', views.FinishedGoodCreateView.as_view(), name='finished_good_add'),
    path('finished-goods/<int:pk>/edit/', views.FinishedGoodUpdateView.as_view(), name='finished_good_edit'),
    path('finished-goods/<int:pk>/delete/', views.FinishedGoodDeleteView.as_view(), name='finished_good_delete'),

    path('stock-movements/', views.StockMovementListView.as_view(), name='stock_movement_list'),
    path('stock-movements/add/', views.StockMovementCreateView.as_view(), name='stock_movement_add'),

    path('product-recipes/', views.ProductRecipeListView.as_view(), name='product_recipe_list'),
    path('product-recipes/add/', views.ProductRecipeCreateView.as_view(), name='product_recipe_add'),
    path('product-recipes/<int:pk>/edit/', views.ProductRecipeUpdateView.as_view(), name='product_recipe_edit'),
    path('product-recipes/<int:pk>/delete/', views.ProductRecipeDeleteView.as_view(), name='product_recipe_delete'),

    path('products/', views.ProductListView.as_view(), name='product_list'),
    path('products/add/', views.ProductCreateView.as_view(), name='product_add'),
    path('products/<int:pk>/edit/', views.ProductUpdateView.as_view(), name='product_edit'),
    path('products/<int:pk>/delete/', views.ProductDeleteView.as_view(), name='product_delete'),

    path('stock-in/', views.StockInListView.as_view(), name='stockin_list'),
    path('stock-in/add/', views.StockInCreateView.as_view(), name='stockin_add'),
    path('stock-in/<int:pk>/edit/', views.StockInUpdateView.as_view(), name='stockin_edit'),

    path('ajax/add-material/', views.ajax_add_material, name='ajax_add_material'),
    path('ajax/stockin/<int:pk>/details/', views.ajax_stockin_details, name='ajax_stockin_details'),
    path('ajax/stockin/<int:pk>/delete/', views.ajax_stockin_delete, name='ajax_stockin_delete'),
    path('ajax/recipe/<int:pk>/details/', views.ajax_recipe_details, name='ajax_recipe_details'),
    path('ajax/check-materials/', views.ajax_check_materials, name='ajax_check_materials'),

    path('raw-material-movements/', views.RawMaterialMovementListView.as_view(), name='raw_material_movement_list'),
    path('raw-material-movements/add/', views.RawMaterialMovementCreateView.as_view(), name='raw_material_movement_add'),
    path('raw-material-movements/<int:pk>/edit/', views.RawMaterialMovementUpdateView.as_view(), name='raw_material_movement_edit'),
    path('raw-material-movements/<int:pk>/delete/', views.RawMaterialMovementDeleteView.as_view(), name='raw_material_movement_delete'),

    path('raw-material-inventory/', views.RawMaterialInventoryStatusView.as_view(), name='raw_material_inventory_status'),

    path('productions/', views.ProductionListView.as_view(), name='production_list'),
    path('productions/add/', views.ProductionCreateView.as_view(), name='production_add'),
    path('productions/<int:pk>/', views.ProductionDetailView.as_view(), name='production_detail'),
    path('productions/<int:pk>/edit/', views.ProductionUpdateView.as_view(), name='production_edit'),
    path('productions/<int:pk>/delete/', views.ProductionDeleteView.as_view(), name='production_delete'),
    path('productions/<int:pk>/complete/', views.complete_production_view, name='production_complete'),
    path('productions/<int:pk>/cancel/', views.cancel_production_view, name='production_cancel'),
    path('productions/<int:pk>/details/add/', views.ProductionDetailCreateView.as_view(), name='production_detail_add'),

    path('ajax/production/<int:pk>/details/', views.ajax_production_details, name='ajax_production_details'),
    path('ajax/production/<int:pk>/check-materials/', views.ajax_check_material_sufficiency, name='ajax_check_material_sufficiency'),
    path('ajax/production/<int:pk>/start/', views.ajax_start_production, name='ajax_start_production'),
    path('ajax/production/<int:pk>/complete/', views.ajax_complete_production, name='ajax_complete_production'),
    path('ajax/production/<int:pk>/cancel/', views.ajax_cancel_production, name='ajax_cancel_production'),
    path('ajax/production/<int:pk>/materials/', views.ajax_get_production_materials, name='ajax_get_production_materials'),

    path('ajax/check-single-product-materials/', views.ajax_check_single_product_materials, name='ajax_check_single_product_materials'),
    path('ajax/check-single-product-materials-with-allocations/', views.ajax_check_single_product_materials_with_allocations, name='ajax_check_single_product_materials_with_allocations'),
    path('ajax/check-batch-materials/', views.ajax_check_batch_materials, name='ajax_check_batch_materials'),

    path('finished-goods-inventory/', views.finished_goods_inventory_list, name='finished_goods_inventory_list'),
    path('ajax/expire-goods/', views.ajax_expire_goods, name='ajax_expire_goods'),

    path('api/products/<int:pk>/', views.product_api_detail, name='product_api_detail'),

    path('ajax/product/<int:pk>/recipes/', views.ajax_product_recipes, name='ajax_product_recipes'),
] 