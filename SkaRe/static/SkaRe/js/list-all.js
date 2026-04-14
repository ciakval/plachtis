/* List All Participants - Table Management */

document.addEventListener('DOMContentLoaded', function() {
    // Exit if not on the list-all page
    if (!document.getElementById('participantsTable')) {
        return;
    }
    
    // Initialize column visibility
    updateColumnVisibility();
    updateCounts();
    
    // Column toggle event listeners
    document.querySelectorAll('.column-toggle').forEach(function(checkbox) {
        checkbox.addEventListener('change', updateColumnVisibility);
    });
    
    // Search filter
    document.getElementById('searchFilter').addEventListener('input', filterTable);
    
    // Type filter
    document.getElementById('typeFilter').addEventListener('change', filterTable);

    // Export button
    const exportButton = document.getElementById('exportCsvButton');
    if (exportButton) {
        exportButton.addEventListener('click', exportVisibleRowsToCsv);
    }
});

function updateColumnVisibility() {
    document.querySelectorAll('.column-toggle').forEach(function(checkbox) {
        const column = checkbox.dataset.column;
        const isVisible = checkbox.checked;
        
        // Update header
        document.querySelectorAll('th[data-col="' + column + '"]').forEach(function(th) {
            th.classList.toggle('hidden-column', !isVisible);
        });
        
        // Update cells
        document.querySelectorAll('td[data-col="' + column + '"]').forEach(function(td) {
            td.classList.toggle('hidden-column', !isVisible);
        });
    });
}

function filterTable() {
    const searchText = document.getElementById('searchFilter').value.toLowerCase();
    const typeFilter = document.getElementById('typeFilter').value;
    
    const rows = document.querySelectorAll('#participantsTable tbody tr');
    let visibleCount = 0;
    
    rows.forEach(function(row) {
        const rowType = row.dataset.type;
        const rowText = row.textContent.toLowerCase();
        
        const matchesType = !typeFilter || rowType === typeFilter;
        const matchesSearch = !searchText || rowText.includes(searchText);
        
        if (matchesType && matchesSearch) {
            row.style.display = '';
            visibleCount++;
        } else {
            row.style.display = 'none';
        }
    });
    
    document.getElementById('visibleCount').textContent = visibleCount;
}

function updateCounts() {
    const totalRows = document.querySelectorAll('#participantsTable tbody tr').length;
    document.getElementById('totalCount').textContent = totalRows;
    document.getElementById('visibleCount').textContent = totalRows;
}

function setPreset(preset) {
    // First, uncheck all
    document.querySelectorAll('.column-toggle').forEach(function(cb) {
        cb.checked = false;
    });
    
    const presets = {
        'basic': ['type', 'firstname', 'lastname', 'dob', 'category'],
        'dietary': ['type', 'firstname', 'lastname', 'dietary'],
        'health': ['type', 'firstname', 'lastname', 'health'],
        'contact': ['type', 'firstname', 'lastname', 'email', 'phone', 'hometown'],
        'all': ['type', 'firstname', 'lastname', 'nickname', 'dob', 'category', 'unit', 'division', 'email', 'phone', 'hometown', 'arrival', 'created', 'dietary', 'health', 'info']
    };
    
    const columns = presets[preset] || presets['basic'];
    
    columns.forEach(function(col) {
        const checkbox = document.querySelector('.column-toggle[data-column="' + col + '"]');
        if (checkbox) checkbox.checked = true;
    });
    
    updateColumnVisibility();
}

let sortDirection = {};
let currentSortColumn = null;

function sortTable(column) {
    const table = document.getElementById('participantsTable');
    const tbody = table.querySelector('tbody');
    const rows = Array.from(tbody.querySelectorAll('tr'));
    
    // Toggle direction
    sortDirection[column] = !sortDirection[column];
    const ascending = sortDirection[column];
    currentSortColumn = column;
    
    // Update sort icons
    updateSortIcons(column, ascending);
    
    rows.sort(function(a, b) {
        const aCell = a.querySelector('td[data-col="' + column + '"]');
        const bCell = b.querySelector('td[data-col="' + column + '"]');
        
        let aVal = aCell ? aCell.textContent.trim() : '';
        let bVal = bCell ? bCell.textContent.trim() : '';
        
        // Handle dates and date-times
        if (column === 'dob' || column === 'created') {
            const parseDate = function(str, withTime) {
                const normalized = (str || '').trim();
                if (!normalized || normalized === '-') {
                    return new Date(0);
                }
                const dateTimeParts = normalized.split(' ');
                const datePart = dateTimeParts[0] || '';
                const dateParts = datePart.split('.');
                if (dateParts.length !== 3) {
                    return new Date(0);
                }

                const day = parseInt(dateParts[0], 10);
                const month = parseInt(dateParts[1], 10);
                const year = parseInt(dateParts[2], 10);
                if ([day, month, year].some(Number.isNaN)) {
                    return new Date(0);
                }

                if (withTime) {
                    const timePart = dateTimeParts[1] || '';
                    const timeParts = timePart.split(':');
                    const hours = parseInt(timeParts[0], 10) || 0;
                    const minutes = parseInt(timeParts[1], 10) || 0;
                    return new Date(year, month - 1, day, hours, minutes);
                }

                return new Date(year, month - 1, day);
            };
            aVal = parseDate(aVal, column === 'created');
            bVal = parseDate(bVal, column === 'created');
            return ascending ? aVal - bVal : bVal - aVal;
        }
        
        // String comparison
        return ascending ? aVal.localeCompare(bVal) : bVal.localeCompare(aVal);
    });
    
    // Re-append sorted rows
    rows.forEach(function(row) {
        tbody.appendChild(row);
    });
}

function updateSortIcons(activeColumn, ascending) {
    // Reset all icons to default
    document.querySelectorAll('.sort-icon').forEach(function(icon) {
        icon.classList.remove('bi-arrow-up', 'bi-arrow-down');
        icon.classList.add('bi-arrow-down-up');
    });
    
    // Set active column icon
    const activeIcon = document.querySelector('.sort-icon[data-col="' + activeColumn + '"]');
    if (activeIcon) {
        activeIcon.classList.remove('bi-arrow-down-up');
        activeIcon.classList.add(ascending ? 'bi-arrow-up' : 'bi-arrow-down');
    }
}

function exportVisibleRowsToCsv() {
    const table = document.getElementById('participantsTable');
    if (!table) {
        return;
    }

    const visibleColumns = Array.from(table.querySelectorAll('thead th[data-col]')).filter(function(th) {
        return !th.classList.contains('hidden-column');
    });

    const visibleRows = Array.from(table.querySelectorAll('tbody tr')).filter(function(row) {
        return row.style.display !== 'none';
    });

    if (visibleColumns.length === 0 || visibleRows.length === 0) {
        return;
    }

    const csvLines = [];

    const headers = visibleColumns.map(function(th) {
        return _csvEscape(th.textContent);
    });
    csvLines.push(headers.join(','));

    visibleRows.forEach(function(row) {
        const values = visibleColumns.map(function(th) {
            const columnKey = th.dataset.col;
            const cell = row.querySelector('td[data-col="' + columnKey + '"]');
            return _csvEscape(cell ? cell.textContent : '');
        });
        csvLines.push(values.join(','));
    });

    const csvContent = '\ufeff' + csvLines.join('\n');
    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = 'all_participants_filtered.csv';
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);

    showExportConfirmation();
}

// Keep function available for inline onclick fallback.
window.exportVisibleRowsToCsv = exportVisibleRowsToCsv;

function _csvEscape(value) {
    const text = (value || '').toString().replace(/\s+/g, ' ').trim();
    return '"' + text.replace(/"/g, '""') + '"';
}

function showExportConfirmation() {
    const feedback = document.getElementById('exportCsvFeedback');
    if (!feedback) {
        return;
    }

    feedback.classList.remove('d-none');
    window.setTimeout(function() {
        feedback.classList.add('d-none');
    }, 3000);
}

