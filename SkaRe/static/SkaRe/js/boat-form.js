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

function selectBoatClassByName(className) {
    if (!className) return;
    const select = document.getElementById('id_boat_class');
    if (!select) return;
    const lower = className.toLowerCase();
    for (const option of select.options) {
        if (option.text.toLowerCase().includes(lower)) {
            if (!select.value) {  // only if nothing selected yet
                select.value = option.value;
            }
            return;
        }
    }
}

// Sail number lookup on blur
const sailNumberField = document.getElementById('id_sail_number');
if (sailNumberField) {
    sailNumberField.addEventListener('blur', function () {
        const q = this.value.trim();
        if (!q) return;
        fetch(`/boats/api/sail-lookup/?q=${encodeURIComponent(q)}`)
            .then(response => {
                if (!response.ok) return;
                return response.json();
            })
            .then(data => {
                if (!data) return;
                fillIfEmpty('id_name', data.boat_name);
                fillIfEmpty('id_class_supplement', data.subtype);
                fillIfEmpty('id_sail_area', data.sail_area);
                fillIfEmpty('id_harbor_number', data.harbor_number);
                fillIfEmpty('id_harbor_name', data.harbor_name);
                fillIfEmpty('id_contact_person', data.contact_person);
                selectBoatClassByName(data.class_name);
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
            });
    });
}
