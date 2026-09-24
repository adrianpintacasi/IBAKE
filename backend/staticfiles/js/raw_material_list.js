(function() {
    var materialToDeleteId = null;
    $(document).on('click', '.delete-material-btn', function() {
        materialToDeleteId = $(this).data('material-id');
        $('#modalMaterialName').text($(this).data('material-name'));
        const modal = new bootstrap.Modal(document.getElementById('deleteMaterialModal'));
        modal.show();
    });
    $('#confirmDeleteMaterialBtn').on('click', function() {
        if (!materialToDeleteId) return;
        $.ajax({
            url: `/inventory/raw-materials/${materialToDeleteId}/delete/`,
            type: 'POST',
            data: {csrfmiddlewaretoken: window.csrftoken || ''},
            success: function() {
                $(`button[data-material-id="${materialToDeleteId}"]`).closest('tr').remove();
                const modal = bootstrap.Modal.getInstance(document.getElementById('deleteMaterialModal'));
                modal.hide();
            },
            error: function() {
                alert('Failed to delete material.');
            }
        });
    });
})(); 