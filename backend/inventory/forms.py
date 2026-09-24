from django import forms
from .models import RawMaterial, FinishedGood, StockMovement, ProductRecipe, Product, StockIn, StockInDetail, ProductRecipeDetail, RawMaterialMovement, Production, ProductionDetail, ProductionBatchProduct
from employee.models import Employee
from django.utils import timezone
from django_select2.forms import ModelSelect2Widget, Select2Widget
from django.forms.models import inlineformset_factory

class RawMaterialForm(forms.ModelForm):
    class Meta:
        model = RawMaterial
        exclude = ['code']
        fields = ['name', 'brand', 'description', 'unit', 'category', 'minimum_stock', 'unit_cost', 'base_unit', 'unit_conversion_factor']
        widgets = {
            'description': forms.Textarea(attrs={'rows': 3}),
        }

class FinishedGoodForm(forms.ModelForm):
    class Meta:
        model = FinishedGood
        fields = ['name', 'description', 'unit', 'category', 'minimum_stock', 'unit_price']
        widgets = {
            'description': forms.Textarea(attrs={'rows': 3}),
        }

class StockMovementForm(forms.ModelForm):
    class Meta:
        model = StockMovement
        fields = ['movement_number', 'movement_type', 'raw_material', 'finished_good', 'quantity', 'notes']
        widgets = {
            'notes': forms.Textarea(attrs={'rows': 3}),
        }

class ProductRecipeForm(forms.ModelForm):
    class Meta:
        model = ProductRecipe
        fields = ['employee', 'product', 'description', 'is_active']
        widgets = {
            'employee': forms.Select(attrs={'class': 'form-select'}),
            'product': forms.Select(attrs={'class': 'form-select'}),
            'description': forms.Textarea(attrs={'rows': 3}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

class ProductRecipeDetailForm(forms.ModelForm):
    material = forms.ModelChoiceField(
        queryset=RawMaterial.objects.all(),
        widget=Select2Widget(attrs={'class': 'searchable-dropdown material-select'}),
        required=True,
        label='Material',
    )

    class Meta:
        model = ProductRecipeDetail
        fields = ['material', 'quantity', 'unit', 'notes']
        widgets = {
            'unit': forms.TextInput(attrs={'class': 'form-control unit-input'}),
            'quantity': forms.NumberInput(attrs={'class': 'form-control'}),
            'notes': forms.Textarea(attrs={'rows': 2, 'class': 'form-control'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Autofill unit from material if not set, only for existing instances
        if self.instance and self.instance.pk and self.instance.material and not self.instance.unit:
            self.fields['unit'].initial = self.instance.material.unit

ProductRecipeDetailFormSet = inlineformset_factory(
    ProductRecipe,
    ProductRecipeDetail,
    form=ProductRecipeDetailForm,
    extra=1,
    can_delete=True,
    min_num=1,
    validate_min=True
)

class StockMovementFilterForm(forms.Form):
    raw_material = forms.ModelChoiceField(queryset=RawMaterial.objects.all(), required=False, empty_label="All Raw Materials")
    finished_good = forms.ModelChoiceField(queryset=FinishedGood.objects.all(), required=False, empty_label="All Finished Goods")
    movement_type = forms.ChoiceField(choices=[('', 'All Types')] + StockMovement.MOVEMENT_TYPE_CHOICES, required=False)
    date_from = forms.DateField(required=False, widget=forms.DateInput(attrs={'type': 'date'}))
    date_to = forms.DateField(required=False, widget=forms.DateInput(attrs={'type': 'date'}))

class ProductForm(forms.ModelForm):
    class Meta:
        model = Product
        fields = ['name', 'category', 'description', 'base_price', 'selling_price', 'shelf_life', 'is_active']
        widgets = {
            'description': forms.Textarea(attrs={'rows': 3}),
        }

class StockInForm(forms.ModelForm):
    class Meta:
        model = StockIn
        fields = ['employee', 'reference_number', 'payment_method', 'notes']
        widgets = {
            'notes': forms.Textarea(attrs={'rows': 2}),
            'payment_method': forms.Select(attrs={'class': 'form-select'}),
        }

class StockInDetailForm(forms.ModelForm):
    material = forms.ModelChoiceField(
        queryset=RawMaterial.objects.all(),
        widget=Select2Widget(attrs={'class': 'searchable-dropdown material-select'}),
        required=True,
        label='Material',
    )
    class Meta:
        model = StockInDetail
        fields = ['material', 'unit', 'quantity', 'unit_price', 'expiry_date']
        widgets = {
            'expiry_date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['unit'].widget.attrs.update({'class': 'form-control unit-input'})
        self.fields['quantity'].widget.attrs.update({'class': 'form-control'})
        self.fields['unit_price'].widget.attrs.update({'class': 'form-control unit-price-input'})
        # Autofill unit_price from material if not set, only for existing instances
        if self.instance and self.instance.pk and self.instance.material and not self.instance.unit_price:
            self.fields['unit_price'].initial = self.instance.material.unit_cost 

class RawMaterialMovementForm(forms.ModelForm):
    remaining_quantity = forms.DecimalField(
        required=False,
        widget=forms.NumberInput(attrs={
            'class': 'form-control', 
            'readonly': 'readonly',
            'style': 'background-color: #e9ecef;'
        }),
        help_text='Shows how much of this movement has not been consumed yet'
    )
    
    class Meta:
        model = RawMaterialMovement
        fields = ['movement_type', 'raw_material', 'quantity', 'remaining_quantity', 'unit', 'reference', 'notes']
        widgets = {
            'notes': forms.Textarea(attrs={'rows': 2, 'class': 'form-control'}),
            'reference': forms.TextInput(attrs={'class': 'form-control'}),
            'unit': forms.TextInput(attrs={'class': 'form-control'}),
            'quantity': forms.NumberInput(attrs={'class': 'form-control'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # For existing instances, populate remaining_quantity
        if self.instance and self.instance.pk:
            self.fields['remaining_quantity'].initial = self.instance.remaining_quantity
        else:
            # For new instances, hide the remaining_quantity field since it's not relevant yet
            self.fields['remaining_quantity'].widget = forms.HiddenInput()
    
    def save(self, commit=True):
        # Don't allow users to manually change remaining_quantity
        # It should only be updated by the system during production consumption
        instance = super().save(commit=False)
        if self.instance.pk:
            # Keep the original remaining_quantity value
            instance.remaining_quantity = self.instance.remaining_quantity
        if commit:
            instance.save()
        return instance

class ProductionForm(forms.ModelForm):
    class Meta:
        model = Production
        fields = [
            'production_number', 'date_started', 'date_finished', 
            'product', 'quantity_produced', 'unit', 'employee', 
            'notes', 'wastage_notes'
        ]
        widgets = {
            'date_started': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'date_finished': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'product': forms.Select(attrs={'class': 'form-select'}),
            'quantity_produced': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': '0'}),
            'unit': forms.TextInput(attrs={'class': 'form-control'}),
            'employee': forms.Select(attrs={'class': 'form-select'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'wastage_notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }

    def __init__(self, *args, **kwargs):
        print(f"DEBUG: ProductionForm.__init__ called with args: {args}, kwargs: {kwargs}")
        super().__init__(*args, **kwargs)
        
        # Check if form can be edited
        if self.instance and not self.instance.can_edit():
            for field in self.fields:
                self.fields[field].disabled = True
        
        # Set default unit for production (typically 'pcs' for bakery products)
        if not self.instance.pk:
            self.fields['unit'].initial = 'pcs'
            print("DEBUG: Set default unit to 'pcs' for new production")
        
        # Make some fields not required for draft saves
        if not self.instance.pk:  # New production
            self.fields['product'].required = False
            self.fields['quantity_produced'].required = False
            self.fields['employee'].required = False
            print("DEBUG: Made fields optional for new production")
        
        print(f"DEBUG: ProductionForm.__init__ completed successfully")
        
    def clean(self):
        cleaned_data = super().clean()
        print(f"DEBUG: ProductionForm.clean called with cleaned_data keys: {list(cleaned_data.keys())}")
        
        # For the new workflow, we always use the unified products approach
        # No need for complex validation since materials are checked automatically
        print("DEBUG: Using unified products approach - skipping single product validation")
        
        # Remove product and quantity_produced from cleaned_data to avoid validation errors
        # These fields are not needed in the unified approach
        if 'product' in cleaned_data:
            del cleaned_data['product']
        if 'quantity_produced' in cleaned_data:
            del cleaned_data['quantity_produced']
        
        print(f"DEBUG: ProductionForm.clean completed with cleaned_data keys: {list(cleaned_data.keys())}")
        return cleaned_data

class ProductionDetailForm(forms.ModelForm):
    class Meta:
        model = ProductionDetail
        fields = ['raw_material', 'quantity_used', 'unit', 'source_batch', 'notes']
        widgets = {
            'notes': forms.Textarea(attrs={'rows': 3, 'class': 'form-control'}),
            'raw_material': forms.Select(attrs={'class': 'form-control', 'id': 'material-select'}),
            'quantity_used': forms.NumberInput(attrs={'class': 'form-control', 'min': '0.01', 'step': '0.01'}),
            'unit': forms.TextInput(attrs={'class': 'form-control', 'readonly': 'readonly'}),
            'source_batch': forms.Select(attrs={'class': 'form-control'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Set initial unit based on raw material
        if 'raw_material' in self.data:
            try:
                material_id = int(self.data.get('raw_material'))
                material = RawMaterial.objects.get(pk=material_id)
                self.fields['unit'].initial = material.unit
            except (ValueError, RawMaterial.DoesNotExist):
                pass
        elif self.instance.pk and self.instance.raw_material:
            self.fields['unit'].initial = self.instance.raw_material.unit 

class ProductionBatchProductForm(forms.ModelForm):
    class Meta:
        model = ProductionBatchProduct
        fields = ['product', 'quantity', 'unit']
        widgets = {
            'product': forms.Select(attrs={'class': 'form-select product-select'}),
            'quantity': forms.NumberInput(attrs={'class': 'form-control', 'min': '1', 'step': '1', 'placeholder': '0'}),
            'unit': forms.TextInput(attrs={'class': 'form-control', 'value': 'pcs'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Set default unit if not provided
        if not self.instance.pk:
            self.fields['unit'].initial = 'pcs'

class ProductionBatchProductFormSet(forms.inlineformset_factory(
    Production,
    ProductionBatchProduct,
    form=ProductionBatchProductForm,
    extra=3,  # Allow up to 3 new forms by default
    can_delete=True,
    min_num=1,  # Require at least 1 product
    validate_min=True,
    max_num=10  # Allow up to 10 products total
)):
    def clean(self):
        super().clean()
        if any(self.errors):
            return

        # Check if at least one form has data
        forms_with_data = 0
        for form in self.forms:
            if form.cleaned_data and not form.cleaned_data.get('DELETE', False):
                forms_with_data += 1

        if forms_with_data == 0:
            raise forms.ValidationError("At least one product must be added to the production batch.")

class RawMaterialInventoryFilterForm(forms.Form):
    STATUS_CHOICES = [
        ('', 'All Status'),
        ('sufficient', 'Sufficient'),
        ('low', 'Low Stock'),
        ('out_of_stock', 'Out of Stock'),
    ]
    
    search = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Search material name...'
        })
    )
    
    status = forms.ChoiceField(
        choices=STATUS_CHOICES, 
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    category = forms.ChoiceField(
        choices=[],
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Get unique categories
        categories = RawMaterial.objects.values_list('category', flat=True).distinct().order_by('category')
        category_choices = [('', 'All Categories')] + [(cat, cat) for cat in categories if cat]
        self.fields['category'].choices = category_choices 