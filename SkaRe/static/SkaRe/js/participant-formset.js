/* Participant Formset Management */

document.addEventListener('DOMContentLoaded', function() {
    const totalFormsInput = document.querySelector('#id_participants-TOTAL_FORMS');
    const tableBody = document.querySelector('#participant-table-body');
    const addButton = document.querySelector('#add-participant');
    
    // Exit if elements don't exist (not on a participant formset page)
    if (!totalFormsInput || !tableBody || !addButton) {
        return;
    }
    
    // Function to update row numbers
    function updateRowNumbers() {
        const rows = tableBody.querySelectorAll('.participant-row:not([style*="display: none"])');
        rows.forEach((row, index) => {
            row.querySelector('.participant-number').textContent = index + 1;
        });
    }
    
    // Add new participant row
    addButton.addEventListener('click', function() {
        const currentFormCount = parseInt(totalFormsInput.value);
        const emptyForm = document.querySelector('#empty-participant-form tr').cloneNode(true);
        
        // Replace __prefix__ with actual form number
        emptyForm.innerHTML = emptyForm.innerHTML.replace(/__prefix__/g, currentFormCount);
        emptyForm.dataset.formIndex = currentFormCount;
        
        tableBody.appendChild(emptyForm);
        totalFormsInput.value = currentFormCount + 1;
        
        updateRowNumbers();
    });
    
    // Remove participant row
    tableBody.addEventListener('click', function(e) {
        if (e.target.closest('.remove-participant')) {
            const row = e.target.closest('.participant-row');
            const deleteCheckbox = row.querySelector('input[name$="-DELETE"]');
            
            if (deleteCheckbox) {
                deleteCheckbox.checked = true;
                row.style.display = 'none';
            } else {
                row.remove();
            }
            
            updateRowNumbers();
        }
    });
    
    // Hide rows that are marked for deletion (on page load, e.g., after validation errors)
    function hideDeletedRows() {
        const deleteCheckboxes = tableBody.querySelectorAll('input[name$="-DELETE"]');
        deleteCheckboxes.forEach(checkbox => {
            if (checkbox.checked) {
                const row = checkbox.closest('.participant-row');
                if (row) {
                    row.style.display = 'none';
                }
            }
        });
    }
    
    // Initial row numbering and hide deleted rows
    hideDeletedRows();
    updateRowNumbers();
});

