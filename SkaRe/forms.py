from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm
from .models import Unit, RegularParticipant, IndividualParticipant, Organizer


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
        label="Scout Unit Name"
    )
    scout_unit_evidence_id = forms.CharField(
        max_length=50,
        required=True,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g., 523.10'}),
        label="Evidence ID"
    )
    
    # Entity fields
    contact_email = forms.EmailField(
        widget=forms.EmailInput(attrs={'class': 'form-control'}),
        label="Contact Email"
    )
    contact_phone = forms.CharField(
        max_length=20,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': '+420 123 456 789'}),
        label="Contact Phone"
    )
    expected_arrival = forms.DateTimeField(
        required=False,
        widget=forms.DateTimeInput(attrs={'class': 'form-control', 'type': 'datetime-local'}),
        label="Expected Arrival"
    )
    expected_departure = forms.DateTimeField(
        required=False,
        widget=forms.DateTimeInput(attrs={'class': 'form-control', 'type': 'datetime-local'}),
        label="Expected Departure"
    )
    home_town = forms.CharField(
        max_length=200,
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control'}),
        label="Home Town"
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
    
    class Meta:
        model = RegularParticipant
        fields = [
            'first_name',
            'last_name',
            'nickname',
            'date_of_birth',
            'category',
            'health_restrictions',
            'dietary_restrictions',
            'relevant_information',
        ]
        widgets = {
            'first_name': forms.TextInput(attrs={'class': 'form-control form-control-sm', 'placeholder': 'First name'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control form-control-sm', 'placeholder': 'Last name'}),
            'nickname': forms.TextInput(attrs={'class': 'form-control form-control-sm', 'placeholder': 'Nickname'}),
            'date_of_birth': forms.DateInput(attrs={'class': 'form-control form-control-sm', 'type': 'date'}),
            'category': forms.Select(attrs={'class': 'form-control form-control-sm'}),
            'health_restrictions': forms.Textarea(attrs={'class': 'form-control form-control-sm', 'rows': 2, 'placeholder': 'Health restrictions'}),
            'dietary_restrictions': forms.Textarea(attrs={'class': 'form-control form-control-sm', 'rows': 2, 'placeholder': 'Dietary restrictions'}),
            'relevant_information': forms.Textarea(attrs={'class': 'form-control form-control-sm', 'rows': 2, 'placeholder': 'Relevant information'}),
        }


# Formset for handling multiple participants
RegularParticipantFormSet = forms.formset_factory(
    RegularParticipantForm,
    extra=3,  # Start with 3 empty forms
    can_delete=True
)


class IndividualParticipantRegistrationForm(forms.ModelForm):
    """Form for registering an individual participant."""
    
    # Entity fields
    contact_email = forms.EmailField(
        widget=forms.EmailInput(attrs={'class': 'form-control'}),
        label="Contact Email"
    )
    contact_phone = forms.CharField(
        max_length=20,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': '+420 123 456 789'}),
        label="Contact Phone"
    )
    expected_arrival = forms.DateTimeField(
        required=False,
        widget=forms.DateTimeInput(attrs={'class': 'form-control', 'type': 'datetime-local'}),
        label="Expected Arrival"
    )
    expected_departure = forms.DateTimeField(
        required=False,
        widget=forms.DateTimeInput(attrs={'class': 'form-control', 'type': 'datetime-local'}),
        label="Expected Departure"
    )
    home_town = forms.CharField(
        max_length=200,
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control'}),
        label="Home Town"
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
            'category',
            'health_restrictions',
            'dietary_restrictions',
            'relevant_information',
        ]
        widgets = {
            'first_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'First name'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Last name'}),
            'nickname': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nickname (optional)'}),
            'date_of_birth': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'category': forms.Select(attrs={'class': 'form-control'}),
            'health_restrictions': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Any health restrictions or medical conditions'}),
            'dietary_restrictions': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Any dietary restrictions or preferences'}),
            'relevant_information': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Any relevant information'}),
        }


class OrganizerRegistrationForm(forms.ModelForm):
    """Form for registering an organizer."""
    
    # Entity fields
    contact_email = forms.EmailField(
        widget=forms.EmailInput(attrs={'class': 'form-control'}),
        label="Contact Email"
    )
    contact_phone = forms.CharField(
        max_length=20,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': '+420 123 456 789'}),
        label="Contact Phone"
    )
    expected_arrival = forms.DateTimeField(
        required=False,
        widget=forms.DateTimeInput(attrs={'class': 'form-control', 'type': 'datetime-local'}),
        label="Expected Arrival"
    )
    expected_departure = forms.DateTimeField(
        required=False,
        widget=forms.DateTimeInput(attrs={'class': 'form-control', 'type': 'datetime-local'}),
        label="Expected Departure"
    )
    home_town = forms.CharField(
        max_length=200,
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control'}),
        label="Home Town"
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
            'category',
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
            'first_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'First name'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Last name'}),
            'nickname': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nickname (optional)'}),
            'date_of_birth': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'category': forms.Select(attrs={'class': 'form-control'}),
            'health_restrictions': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Any health restrictions or medical conditions'}),
            'dietary_restrictions': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Any dietary restrictions or preferences'}),
            'relevant_information': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Any relevant information'}),
            'division': forms.Select(attrs={'class': 'form-control'}),
            'transport': forms.Select(attrs={'class': 'form-control'}),
            'need_lift': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'want_travel_order': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'accommodation': forms.Select(attrs={'class': 'form-control'}),
            'codex_agreement': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
