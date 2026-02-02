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
        'all': ['type', 'firstname', 'lastname', 'nickname', 'dob', 'category', 'unit', 'division', 'email', 'phone', 'hometown', 'arrival', 'dietary', 'health', 'info']
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
        
        // Handle dates
        if (column === 'dob') {
            const parseDate = function(str) {
                const parts = str.split('.');
                if (parts.length === 3) {
                    return new Date(parts[2], parts[1] - 1, parts[0]);
                }
                return new Date(0);
            };
            aVal = parseDate(aVal);
            bVal = parseDate(bVal);
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

