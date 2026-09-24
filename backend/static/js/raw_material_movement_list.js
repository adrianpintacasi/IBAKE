(function() {
    var movementToDeleteId = null;
    $(document).on('click', '.delete-movement-btn', function() {
        movementToDeleteId = $(this).data('movement-id');
        $('#modalMovementNumber').text($(this).data('movement-number'));
        $('#modalMaterial').text($(this).data('material'));
        const modal = new bootstrap.Modal(document.getElementById('deleteMovementModal'));
        modal.show();
    });

    $('#confirmDeleteMovementBtn').on('click', function() {
        if (!movementToDeleteId) return;
        
        $.ajax({
            url: `/inventory/raw-material-movements/${movementToDeleteId}/delete/`,
            type: 'POST',
            headers: {
                'X-Requested-With': 'XMLHttpRequest'
            },
            data: {
                csrfmiddlewaretoken: window.csrftoken || ''
            },
            success: function(response) {
                if (response.status === 'success') {
                    $(`button[data-movement-id="${movementToDeleteId}"]`).closest('tr').fadeOut(400, function() {
                        $(this).remove();
                    });
                    const modal = bootstrap.Modal.getInstance(document.getElementById('deleteMovementModal'));
                    modal.hide();
                } else {
                    alert('Failed to delete movement.');
                }
            },
            error: function(xhr, status, error) {
                console.error('Delete error:', error);
                alert('Failed to delete movement. Please try again.');
            }
        });
    });
})(); 