$(document).ready(function() {
    let lastMaterialSelect = null;
    function getRowTemplate() {
        return `<tr class="form-row align-middle text-center">
            <td style="width:25%">
                <select class="searchable-dropdown form-control material-select" required>
                    <option value="">---------</option>
                    MATERIAL_OPTIONS_PLACEHOLDER
                    <option value="add_new">+ Add new material</option>
                </select>
            </td>
            <td style="width:12%"><input type="text" class="form-control unit-input text-center" required></td>
            <td style="width:12%"><input type="number" class="form-control quantity-input text-center" step="0.01" min="0" required></td>
            <td style="width:12%"><input type="number" class="form-control unit-price-input text-center" step="0.01" min="0" required></td>
            <td style="width:12%"><input type="date" class="form-control expiry-date-input text-center"></td>
            <td style="width:12%" class="total-cell fw-bold text-center">0.00</td>
            <td style="width:12%" class="total-stock-cell fw-bold text-center text-primary">-</td>
            <td style="width:3%">
                <div class="d-grid gap-1">
                    <button type="button" class="btn btn-danger btn-sm delete-row">Delete</button>
                </div>
            </td>
        </tr>`;
    }
    function initSelect2For(selectElem) {
        selectElem.select2({
            width: '100%',
            theme: 'bootstrap-5',
            dropdownParent: $('#stockin-form'),
            templateResult: function (data) {
                if (data.id === 'add_new') {
                    return $('<span class="add-new-material-option"><i class="fas fa-plus-circle me-1"></i> Add new material</span>');
                }
                return data.text;
            },
            templateSelection: function (data) {
                if (data.id === 'add_new') {
                    return $('<span class="add-new-material-option"><i class="fas fa-plus-circle me-1"></i> Add new material</span>');
                }
                return data.text;
            },
            sorter: function(data) {
                var addNew = data.find(function(item) { return item.id === 'add_new'; });
                var blank = data.find(function(item) { return item.id === ''; });
                var rest = data.filter(function(item) { return item.id !== 'add_new' && item.id !== ''; });
                var sorted = [];
                if (blank) sorted.push(blank);
                if (addNew) sorted.push(addNew);
                return sorted.concat(rest);
            }
        });
    }
    function addRowEventListeners(row) {
        const quantityInput = $(row).find('.quantity-input');
        const unitPriceInput = $(row).find('.unit-price-input');
        const materialSelect = $(row).find('.material-select');
        const unitInput = $(row).find('.unit-input');
        quantityInput.on('input', () => { 
            updateTotal(row); 
            updateTotalStock(); 
        });
        unitPriceInput.on('input', () => { 
            updateTotal(row); 
        });
        if (materialSelect.length) {
            initSelect2For(materialSelect);
            materialSelect.on('change', function() {
                const selected = $(this).find('option:selected');
                const value = $(this).val();
                if (value === 'add_new') {
                    lastMaterialSelect = materialSelect;
                    const modal = new bootstrap.Modal(document.getElementById('addMaterialModal'));
                    modal.show();
                    // When modal closes, reset select to blank
                    $('#addMaterialModal').on('hidden.bs.modal', function() {
                        materialSelect.val('').trigger('change');
                    });
                } else {
                    const unit = selected.data('unit');
                    const unitCost = selected.data('unitcost');
                    if (unit) unitInput.val(unit);
                    if (unitCost !== undefined) unitPriceInput.val(unitCost);
                    updateTotal(row);
                    updateTotalStock();
                }
            });
        }
        $(row).find('.delete-row').on('click', function() {
            $(row).remove();
        });
    }
    function updateTotal(row) {
        const quantity = parseFloat($(row).find('.quantity-input').val()) || 0;
        const unitPrice = parseFloat($(row).find('.unit-price-input').val()) || 0;
        const total = quantity * unitPrice;
        $(row).find('.total-cell').text(total.toFixed(2));
    }
    function updateTotalStock() {
        $('#formset-table tbody tr').each(function() {
            const $row = $(this);
            const quantity = parseFloat($row.find('.quantity-input').val()) || 0;
            const materialSelect = $row.find('.material-select');
            let totalStockText = '-';
            
            if (materialSelect.length && materialSelect.val()) {
                const selected = materialSelect.find('option:selected');
                const baseUnit = selected.data('baseunit') || '';
                const conversionFactor = parseFloat(selected.data('unitconversionfactor')) || 1;
                
                if (quantity > 0) {
                    const totalStock = quantity * conversionFactor;
                    // Format the number to remove unnecessary decimals
                    const formattedStock = totalStock % 1 === 0 ? 
                        totalStock.toString() : 
                        totalStock.toFixed(2).replace(/\.?0+$/, '');
                    totalStockText = `${formattedStock} ${baseUnit}`;
                }
            }
            
            $row.find('.total-stock-cell').text(totalStockText);
        });
    }
    // Add first row on page load
    const formsetTable = document.getElementById('formset-table').getElementsByTagName('tbody')[0];
    function addNewRow(prefill) {
        let rowTemplate = getRowTemplate();
        rowTemplate = rowTemplate.replace('MATERIAL_OPTIONS_PLACEHOLDER', window.materialOptions || '');
        const $newRow = $(rowTemplate);

        // Set values for each field BEFORE initializing Select2
        if (prefill) {
            if (prefill.material_id || prefill.material) {
                // Always set as string
                $newRow.find('.material-select').val(String(prefill.material_id || prefill.material));
            }
            if (prefill.unit) $newRow.find('.unit-input').val(prefill.unit);
            if (prefill.quantity) $newRow.find('.quantity-input').val(prefill.quantity);
            if (prefill.unit_price) $newRow.find('.unit-price-input').val(prefill.unit_price);
            if (prefill.expiry_date) $newRow.find('.expiry-date-input').val(prefill.expiry_date);
            // Set total cell
            const total = (parseFloat(prefill.quantity) || 0) * (parseFloat(prefill.unit_price) || 0);
            $newRow.find('.total-cell').text(total.toFixed(2));
        }

        formsetTable.appendChild($newRow[0]);
        addRowEventListeners($newRow);

        // Always trigger change after Select2 is initialized
        $newRow.find('.material-select').trigger('change');

        // After adding a new row:
        updateTotalStock();
    }

    // Prefill rows if editing, else add one blank row
    if (window.stockInDetails && window.stockInDetails.length > 0) {
        window.stockInDetails.forEach(function(detail) {
            addNewRow({
                material_id: detail.material_id || detail.material, // support both keys
                unit: detail.unit,
                quantity: detail.quantity,
                unit_price: detail.unit_price,
                expiry_date: detail.expiry_date
            });
        });
    } else {
        addNewRow();
    }

    // Add row on button click
    $('#add-form').on('click', function() {
        addNewRow();
    });

    // Handle Add Material form submit
    $('#add-material-form').on('submit', function(e) {
        e.preventDefault();
        const form = this;
        const data = {
            name: form.name.value,
            brand: form.brand.value,
            description: form.description.value,
            category: form.category.value,
            unit: form.unit.value,
            minimum_stock: form.minimum_stock.value,
            unit_cost: form.unit_cost.value
        };
        fetch('/inventory/ajax/add-material/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': document.querySelector('[name=csrfmiddlewaretoken]').value
            },
            body: JSON.stringify(data)
        })
        .then(response => response.json())
        .then(result => {
            if (result.success) {
                // Add the new option to all selects if it doesn't exist
                const optionHtml = `<option value="${result.material.pk}" data-unit="${result.material.unit}" data-unitcost="${result.material.unit_cost}">${result.material.name}${result.material.brand ? ' - ' + result.material.brand : ''}</option>`;
                window.materialOptions += optionHtml;
                $('.material-select').each(function() {
                    if ($(this).find('option[value="' + result.material.pk + '"]').length === 0) {
                        // Insert before the add_new option if present, else at the end
                        var addNewOpt = $(this).find('option[value="add_new"]');
                        if (addNewOpt.length) {
                            $(optionHtml).insertBefore(addNewOpt);
                        } else {
                            $(this).append(optionHtml);
                        }
                    }
                });
                // Select the new material in the select that triggered the modal
                if (lastMaterialSelect) {
                    lastMaterialSelect.val(result.material.pk).trigger('change');
                    lastMaterialSelect.select2('close');
                }
                // Hide modal
                bootstrap.Modal.getInstance(document.getElementById('addMaterialModal')).hide();
                form.reset();
            } else {
                alert(result.error || 'Failed to add material.');
            }
        })
        .catch(() => alert('Failed to add material.'));
    });

    // Serialize table data to hidden input before submit
    $('#stockin-form').on('submit', function(e) {
        const details = [];
        $('#formset-table tbody tr').each(function() {
            const $row = $(this);
            const material = $row.find('.material-select').val();
            const unit = $row.find('.unit-input').val();
            const quantity = $row.find('.quantity-input').val();
            const unit_price = $row.find('.unit-price-input').val();
            const expiry_date = $row.find('.expiry-date-input').val();
            if (material && unit && quantity && unit_price) {
                details.push({
                    material: material,
                    unit: unit,
                    quantity: quantity,
                    unit_price: unit_price,
                    expiry_date: expiry_date
                });
            }
        });
        $('#stockin-details-json').val(JSON.stringify(details));
    });
}); 