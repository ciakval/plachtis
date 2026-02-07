from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm
from django.utils.translation import gettext_lazy as _
from django.core.exceptions import ValidationError
from datetime import datetime
from django.utils import timezone
from .models import Unit, RegularParticipant, IndividualParticipant, Organizer


def validate_czech_phone(value):
    """Validate Czech/Slovak phone number: must be +420/9 digits, +421/9 digits, or just 9 digits."""
    # Remove spaces for validation
    phone_clean = value.replace(' ', '').replace('-', '')
    
    # Check if it starts with +420 or +421
    if phone_clean.startswith('+420'):
        # Extract digits after +420
        digits = phone_clean[4:]  # After '+420'
        if not digits.isdigit() or len(digits) != 9:
            raise ValidationError(_('Phone number must have exactly 9 digits after +420 (e.g., +420 123 456 789)'))
    elif phone_clean.startswith('+421'):
        # Extract digits after +421
        digits = phone_clean[4:]  # After '+421'
        if not digits.isdigit() or len(digits) != 9:
            raise ValidationError(_('Phone number must have exactly 9 digits after +421 (e.g., +421 123 456 789)'))
    elif phone_clean.isdigit() and len(phone_clean) == 9:
        # Just 9 digits without country code
        return value
    else:
        raise ValidationError(_('Phone number must be: +420 followed by 9 digits, +421 followed by 9 digits, or just 9 digits (e.g., +420 123 456 789, +421 123 456 789, or 123 456 789)'))
    
    return value


class UserRegistrationForm(UserCreationForm):
    """Custom user registration form with additional fields."""
    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={'class': 'form-control'})
    )
    first_name = forms.CharField(
        max_length=30,
        required=True,
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    last_name = forms.CharField(
        max_length=30,
        required=True,
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )

    class Meta:
        model = User
        fields = ['username', 'first_name', 'last_name', 'email', 'password1', 'password2']
        widgets = {
            'username': forms.TextInput(attrs={'class': 'form-control'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['password1'].widget.attrs.update({'class': 'form-control'})
        self.fields['password2'].widget.attrs.update({'class': 'form-control'})

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data['email']
        user.first_name = self.cleaned_data['first_name']
        user.last_name = self.cleaned_data['last_name']
        if commit:
            user.save()
        return user


class UnitRegistrationForm(forms.ModelForm):
    """Form for registering a new Unit."""

    # Scout Unit fields
    scout_unit_name = forms.CharField(
        max_length=200,
        required=True,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g., 5. oddíl Koráb'}),
        label=_("Scout Unit Name")
    )
    scout_unit_evidence_id = forms.CharField(
        max_length=50,
        required=True,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g., 523.10'}),
        label=_("Evidence ID")
    )

    # Entity fields
    contact_email = forms.EmailField(
        widget=forms.EmailInput(attrs={'class': 'form-control'}),
        label=_("Contact Email")
    )
    contact_phone = forms.CharField(
        max_length=20,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': '+420 123 456 789'}),
        label=_("Contact Phone"),
        validators=[validate_czech_phone]
    )
    expected_arrival = forms.DateTimeField(
        required=False,
        widget=forms.DateTimeInput(attrs={'class': 'form-control', 'type': 'datetime-local'}, format='%Y-%m-%dT%H:%M'),
        label=_("Expected Arrival"),
        initial=datetime(2026, 4, 30, 16, 0, tzinfo=timezone.get_current_timezone())
    )
    expected_departure = forms.DateTimeField(
        required=False,
        widget=forms.DateTimeInput(attrs={'class': 'form-control', 'type': 'datetime-local'}, format='%Y-%m-%dT%H:%M'),
        label=_("Expected Departure"),
        initial=datetime(2026, 5, 3, 11, 0, tzinfo=timezone.get_current_timezone())
    )
    home_town = forms.CharField(
        max_length=200,
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control'}),
        label=_("Home Town")
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Add 'is-invalid' class to fields with errors
        for field_name, field in self.fields.items():
            if field_name in self.errors:
                if 'class' in field.widget.attrs:
                    field.widget.attrs['class'] += ' is-invalid'
                else:
                    field.widget.attrs['class'] = 'is-invalid'

    class Meta:
        model = Unit
        fields = [
            'contact_person_name',
            'backup_contact_phone',
            'boats_p550',
            'boats_sail',
            'boats_paddle',
            'boats_motor',
            'scarf_count',
            'hat_count',
            'accommodation_expectations',
            'estimated_accommodation_area',
        ]
        widgets = {
            'contact_person_name': forms.TextInput(attrs={'class': 'form-control'}),
            'backup_contact_phone': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '+420 987 654 321'}),
            'boats_p550': forms.NumberInput(attrs={'class': 'form-control', 'min': '0'}),
            'boats_sail': forms.NumberInput(attrs={'class': 'form-control', 'min': '0'}),
            'boats_paddle': forms.NumberInput(attrs={'class': 'form-control', 'min': '0'}),
            'boats_motor': forms.NumberInput(attrs={'class': 'form-control', 'min': '0'}),
            'scarf_count': forms.NumberInput(attrs={'class': 'form-control', 'min': '0'}),
            'hat_count': forms.NumberInput(attrs={'class': 'form-control', 'min': '0'}),
            'accommodation_expectations': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'estimated_accommodation_area': forms.TextInput(attrs={'class': 'form-control'}),
        }


class RegularParticipantForm(forms.ModelForm):
    """Form for adding a regular participant to a unit."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Add 'is-invalid' class to fields with errors
        for field_name, field in self.fields.items():
            if field_name in self.errors:
                if 'class' in field.widget.attrs:
                    field.widget.attrs['class'] += ' is-invalid'
                else:
                    field.widget.attrs['class'] = 'is-invalid'
    
    def full_clean(self):
        """Override to ensure DELETE field is processed.
        
        The DELETE field is added by the formset dynamically, so it might not be
        in self.fields during full_clean(). We manually process it from POST data.
        """
        super().full_clean()
        if not hasattr(self, 'cleaned_data') or self.cleaned_data is None:
            self.cleaned_data = {}
        
        if 'DELETE' not in self.cleaned_data:
            if hasattr(self, 'data') and self.data:
                if hasattr(self, 'prefix') and self.prefix:
                    delete_key = f'{self.prefix}-DELETE'
                    delete_value = self.data.get(delete_key, False)
                else:
                    delete_keys = [k for k in self.data.keys() if k.endswith('-DELETE')]
                    delete_value = self.data.get(delete_keys[0], False) if delete_keys else False
                
                self.cleaned_data['DELETE'] = (delete_value == 'on' or delete_value is True or delete_value == 'True')
            else:
                self.cleaned_data['DELETE'] = False

    class Meta:
        model = RegularParticipant
        fields = [
            'first_name',
            'last_name',
            'nickname',
            'date_of_birth',
            'health_restrictions',
            'dietary_restrictions',
            'relevant_information',
        ]
        widgets = {
            'first_name': forms.TextInput(attrs={'class': 'form-control form-control-sm', 'placeholder': _('First name')}),
            'last_name': forms.TextInput(attrs={'class': 'form-control form-control-sm', 'placeholder': _('Last name')}),
            'nickname': forms.TextInput(attrs={'class': 'form-control form-control-sm', 'placeholder': _('Nickname')}),
            'date_of_birth': forms.DateInput(attrs={'class': 'form-control form-control-sm', 'type': 'date'}, format='%Y-%m-%d'),
            'health_restrictions': forms.Textarea(attrs={'class': 'form-control form-control-sm', 'rows': 2, 'placeholder': _('e.g. Anxiety, asthma')}),
            'dietary_restrictions': forms.Textarea(attrs={'class': 'form-control form-control-sm', 'rows': 2, 'placeholder': _('e.g. Vegetarian, gluten-free')}),
            'relevant_information': forms.Textarea(attrs={'class': 'form-control form-control-sm', 'rows': 2, 'placeholder': _('e.g. Special needs')}),
        }


# Formset factory function for handling multiple participants
def get_participant_formset(extra=3):
    """Get a formset for participants with configurable number of empty forms.
    
    Args:
        extra: Number of empty forms to show (default 3 for new registrations, 0 for editing)
    """
    return forms.modelformset_factory(
        RegularParticipant,
        form=RegularParticipantForm,
        extra=extra,
        can_delete=True
    )


class IndividualParticipantRegistrationForm(forms.ModelForm):
    """Form for registering an individual participant."""

    # Entity fields
    contact_email = forms.EmailField(
        widget=forms.EmailInput(attrs={'class': 'form-control'}),
        label=_("Contact Email")
    )
    contact_phone = forms.CharField(
        max_length=20,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': '+420 123 456 789'}),
        label=_("Contact Phone"),
        validators=[validate_czech_phone]
    )
    expected_arrival = forms.DateTimeField(
        required=False,
        widget=forms.DateTimeInput(attrs={'class': 'form-control', 'type': 'datetime-local'}, format='%Y-%m-%dT%H:%M'),
        label=_("Expected Arrival"),
        initial=datetime(2026, 4, 30, 16, 0, tzinfo=timezone.get_current_timezone())
    )
    expected_departure = forms.DateTimeField(
        required=False,
        widget=forms.DateTimeInput(attrs={'class': 'form-control', 'type': 'datetime-local'}, format='%Y-%m-%dT%H:%M'),
        label=_("Expected Departure"),
        initial=datetime(2026, 5, 3, 11, 0, tzinfo=timezone.get_current_timezone())
    )
    home_town = forms.CharField(
        max_length=200,
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control'}),
        label=_("Home Town")
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Add 'is-invalid' class to fields with errors
        for field_name, field in self.fields.items():
            if field_name in self.errors:
                if 'class' in field.widget.attrs:
                    field.widget.attrs['class'] += ' is-invalid'
                else:
                    field.widget.attrs['class'] = 'is-invalid'

    class Meta:
        model = IndividualParticipant
        fields = [
            'first_name',
            'last_name',
            'nickname',
            'date_of_birth',
            'health_restrictions',
            'dietary_restrictions',
            'relevant_information',
            'boats_p550',
            'boats_sail',
            'boats_paddle',
            'boats_motor',
            'scarf_count',
            'hat_count',
            'accommodation_expectations',
            'estimated_accommodation_area',
        ]
        widgets = {
            'first_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': _('First name')}),
            'last_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': _('Last name')}),
            'nickname': forms.TextInput(attrs={'class': 'form-control', 'placeholder': _('Nickname (optional)')}),
            'date_of_birth': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'health_restrictions': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': _('Any health restrictions or medical conditions')}),
            'dietary_restrictions': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': _('Any dietary restrictions or preferences')}),
            'relevant_information': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': _('Any relevant information')}),
            'boats_p550': forms.NumberInput(attrs={'class': 'form-control', 'min': '0'}),
            'boats_sail': forms.NumberInput(attrs={'class': 'form-control', 'min': '0'}),
            'boats_paddle': forms.NumberInput(attrs={'class': 'form-control', 'min': '0'}),
            'boats_motor': forms.NumberInput(attrs={'class': 'form-control', 'min': '0'}),
            'scarf_count': forms.NumberInput(attrs={'class': 'form-control', 'min': '0'}),
            'hat_count': forms.NumberInput(attrs={'class': 'form-control', 'min': '0'}),
            'accommodation_expectations': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': _('e.g., Small tent, caravan')}),
            'estimated_accommodation_area': forms.TextInput(attrs={'class': 'form-control', 'placeholder': _('e.g., 20 m²')}),
        }


class OrganizerRegistrationForm(forms.ModelForm):
    """Form for registering an organizer."""

    # Entity fields
    contact_email = forms.EmailField(
        widget=forms.EmailInput(attrs={'class': 'form-control'}),
        label=_("Contact Email")
    )
    contact_phone = forms.CharField(
        max_length=20,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': '+420 123 456 789'}),
        label=_("Contact Phone"),
        validators=[validate_czech_phone]
    )
    expected_arrival = forms.DateTimeField(
        required=False,
        widget=forms.DateTimeInput(attrs={'class': 'form-control', 'type': 'datetime-local'}, format='%Y-%m-%dT%H:%M'),
        label=_("Expected Arrival"),
        initial=datetime(2026, 4, 30, 16, 0, tzinfo=timezone.get_current_timezone())
    )
    expected_departure = forms.DateTimeField(
        required=False,
        widget=forms.DateTimeInput(attrs={'class': 'form-control', 'type': 'datetime-local'}, format='%Y-%m-%dT%H:%M'),
        label=_("Expected Departure"),
        initial=datetime(2026, 5, 3, 11, 0, tzinfo=timezone.get_current_timezone())
    )
    home_town = forms.CharField(
        max_length=200,
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control'}),
        label=_("Home Town")
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Add 'is-invalid' class to fields with errors
        for field_name, field in self.fields.items():
            if field_name in self.errors:
                if 'class' in field.widget.attrs:
                    field.widget.attrs['class'] += ' is-invalid'
                else:
                    field.widget.attrs['class'] = 'is-invalid'

    class Meta:
        model = Organizer
        fields = [
            'first_name',
            'last_name',
            'nickname',
            'date_of_birth',
            'health_restrictions',
            'dietary_restrictions',
            'relevant_information',
            'division',
            'transport',
            'need_lift',
            'want_travel_order',
            'accommodation',
            'codex_agreement',
        ]
        widgets = {
            'first_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': _('First name')}),
            'last_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': _('Last name')}),
            'nickname': forms.TextInput(attrs={'class': 'form-control', 'placeholder': _('Nickname (optional)')}),
            'date_of_birth': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'health_restrictions': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': _('Any health restrictions or medical conditions')}),
            'dietary_restrictions': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': _('Any dietary restrictions or preferences')}),
            'relevant_information': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': _('Any relevant information')}),
            'division': forms.Select(attrs={'class': 'form-control'}),
            'transport': forms.Select(attrs={'class': 'form-control'}),
            'need_lift': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'want_travel_order': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'accommodation': forms.Select(attrs={'class': 'form-control'}),
            'codex_agreement': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
