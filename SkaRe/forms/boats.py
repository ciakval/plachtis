from django import forms
from django.utils.translation import gettext_lazy as _
from ..models import BoatClass, Boat


class BoatForm(forms.ModelForm):
    """Form for registering or editing a boat."""

    class Meta:
        model = Boat
        fields = [
            'boat_class', 'class_supplement', 'sail_number', 'name',
            'description', 'sail_area', 'hull_color', 'sail_color',
            'harbor_number', 'harbor_name', 'contact_person', 'contact_phone',
            'vessel_registry_number', 'engine_power_hp', 'willing_to_lend',
        ]
        widgets = {
            'boat_class': forms.Select(attrs={'class': 'form-control'}),
            'class_supplement': forms.TextInput(attrs={'class': 'form-control'}),
            'sail_number': forms.TextInput(attrs={'class': 'form-control', 'id': 'id_sail_number'}),
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'sail_area': forms.NumberInput(attrs={'class': 'form-control', 'min': '0', 'step': '0.01'}),
            'hull_color': forms.TextInput(attrs={'class': 'form-control', 'list': 'hull-color-list'}),
            'sail_color': forms.TextInput(attrs={'class': 'form-control', 'list': 'sail-color-list'}),
            'harbor_number': forms.TextInput(attrs={'class': 'form-control'}),
            'harbor_name': forms.TextInput(attrs={'class': 'form-control'}),
            'contact_person': forms.TextInput(attrs={'class': 'form-control'}),
            'contact_phone': forms.TextInput(attrs={'class': 'form-control'}),
            'vessel_registry_number': forms.TextInput(attrs={'class': 'form-control'}),
            'engine_power_hp': forms.NumberInput(attrs={'class': 'form-control', 'min': '0'}),
            'willing_to_lend': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Build grouped choices for the boat_class select (SAIL optgroup, then OTHER optgroup).
        # widget.choices controls rendering; ModelChoiceField.queryset controls validation.
        sail_pks = list(
            BoatClass.objects.filter(category=BoatClass.Category.SAIL)
            .order_by('order', 'name').values_list('pk', 'name')
        )
        other_pks = list(
            BoatClass.objects.filter(category=BoatClass.Category.OTHER)
            .order_by('order', 'name').values_list('pk', 'name')
        )
        self.fields['boat_class'].widget.choices = (
            [('', '---------')]
            + [(_('Sailboats'), [(str(pk), name) for pk, name in sail_pks])]
            + [(_('Other'), [(str(pk), name) for pk, name in other_pks])]
        )
        self.fields['boat_class'].queryset = BoatClass.objects.order_by('order', 'name')
        self.fields['boat_class'].required = True
        from .registration import validate_event_phone
        self.fields['contact_phone'].validators = [validate_event_phone]
        self.fields['hull_color'].help_text = _('Colour is critical for identifying the boat on the water.')
        self.fields['sail_color'].help_text = _('Colour is critical for identifying the boat on the water.')
        # Note: accessing self.errors here is intentional — Django's errors property
        # calls full_clean() on demand for bound forms, which is the same pattern
        # used by UnitRegistrationForm and others in this codebase.
        for field_name, field in self.fields.items():
            if field_name in self.errors:
                if 'class' in field.widget.attrs:
                    field.widget.attrs['class'] += ' is-invalid'
                else:
                    field.widget.attrs['class'] = 'is-invalid'
