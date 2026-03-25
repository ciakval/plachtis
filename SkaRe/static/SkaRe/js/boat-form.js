// Boat form: sail number registry lookup + unit prefill
// Prefill only fills empty fields. Never overwrites user-typed data.
// Never injects an empty string into a non-empty required field.

function fillIfEmpty(fieldId, value) {
    if (!value) return;  // never inject blank values
    const field = document.getElementById(fieldId);
    if (field && !field.value) {
        field.value = value;
    }
}

// Sail number registry lookup button
const sailLookupBtn = document.getElementById('btn-sail-lookup');
const sailLookupError = document.getElementById('sail-lookup-error');

if (sailLookupBtn) {
    sailLookupBtn.addEventListener('click', function () {
        const q = document.getElementById('id_sail_number').value.trim();
        if (!q) return;  // don't fetch with empty query

        // Reset error state
        sailLookupError.textContent = '';
        sailLookupError.style.display = 'none';

        sailLookupBtn.disabled = true;

        fetch(`/boats/api/sail-lookup/?q=${encodeURIComponent(q)}`)
            .then(response => {
                if (response.status === 404) {
                    sailLookupError.textContent = 'Plachetní číslo nebylo v registru nalezeno.';
                    sailLookupError.style.display = '';
                    return null;
                }
                if (!response.ok) {
                    sailLookupError.textContent = 'Registr plachet je nedostupný.';
                    sailLookupError.style.display = '';
                    return null;
                }
                return response.json();
            })
            .then(data => {
                if (!data) return;

                // Overwrite boat fields regardless of current content
                document.getElementById('id_name').value = data.boat_name || '';
                document.getElementById('id_class_supplement').value = data.subtype || '';
                document.getElementById('id_sail_area').value = data.sail_area || '';

                // Overwrite boat class select
                const select = document.getElementById('id_boat_class');
                if (select && data.class_name) {
                    select.value = '';
                    const lower = data.class_name.toLowerCase();
                    for (const option of select.options) {
                        if (option.text.toLowerCase().includes(lower)) {
                            select.value = option.value;
                            break;
                        }
                    }
                }
                // Do NOT fill harbor_number, harbor_name, contact_person — owner fields
            })
            .catch(() => {
                sailLookupError.textContent = 'Registr plachet je nedostupný.';
                sailLookupError.style.display = '';
            })
            .finally(() => {
                sailLookupBtn.disabled = false;
            });
    });
}

// Unit prefill button
const unitPrefillBtn = document.getElementById('btn-fill-from-unit');
if (unitPrefillBtn) {
    unitPrefillBtn.addEventListener('click', function (e) {
        e.preventDefault();
        fetch('/boats/api/my-unit/')
            .then(response => {
                if (!response.ok) return;
                return response.json();
            })
            .then(data => {
                if (!data) return;
                fillIfEmpty('id_harbor_number', data.harbor_number);
                fillIfEmpty('id_harbor_name', data.harbor_name);
                fillIfEmpty('id_contact_person', data.contact_person);
                fillIfEmpty('id_contact_phone', data.contact_phone);
            });
    });
}
