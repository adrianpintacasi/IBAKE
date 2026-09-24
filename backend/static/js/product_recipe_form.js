// product_recipe_form.js

// Dummy data for materials (replace with actual data from Django context if needed)
const materials = window.recipeMaterials || [];

function createMaterialOptions(selectedId = null) {
    let options = '<option value="">---------</option>';
    materials.forEach(mat => {
        options += `<option value="${mat.id}" ${selectedId == mat.id ? 'selected' : ''}>${mat.name} - ${mat.brand}</option>`;
    });
    return options;
}

function addRecipeRow(data = {}) {
    const table = document.querySelector('#recipe-details-table tbody');
    const row = document.createElement('tr');
    row.innerHTML = `
        <td>
            <select class="form-select material-select" name="material">
                ${createMaterialOptions(data.material)}
            </select>
        </td>
        <td><input type="text" class="form-control unit-input" name="unit" value="${data.unit || ''}"></td>
        <td><input type="number" class="form-control quantity-input" name="quantity" min="0.01" step="0.01" value="${data.quantity || ''}"></td>
        <td><button type="button" class="btn btn-danger btn-sm delete-row-btn">Delete</button></td>
    `;
    table.appendChild(row);
    $(row).find('.material-select').select2({ theme: 'bootstrap-5', width: '100%' });
}

function serializeRecipeRows() {
    const rows = document.querySelectorAll('#recipe-details-table tbody tr');
    const details = [];
    rows.forEach(row => {
        const material = row.querySelector('select[name="material"]').value;
        const unit = row.querySelector('input[name="unit"]').value;
        const quantity = row.querySelector('input[name="quantity"]').value;
        if (material && unit && quantity) {
            details.push({ material, unit, quantity });
        }
    });
    document.getElementById('recipe-details-json').value = JSON.stringify(details);
}

document.addEventListener('DOMContentLoaded', function() {
    // Prefill rows if editing
    if (window.recipeDetails && window.recipeDetails.length > 0) {
        window.recipeDetails.forEach(function(detail) {
            addRecipeRow({
                material: detail.material_id,
                unit: detail.unit,
                quantity: detail.quantity
            });
        });
    } else {
        addRecipeRow();
    }

    document.getElementById('add-row-btn').addEventListener('click', function() {
        addRecipeRow();
    });

    document.querySelector('#recipe-details-table tbody').addEventListener('click', function(e) {
        if (e.target.classList.contains('delete-row-btn')) {
            const row = e.target.closest('tr');
            row.remove();
        }
    });

    document.getElementById('recipe-form').addEventListener('submit', function(e) {
        serializeRecipeRows();
    });
}); 