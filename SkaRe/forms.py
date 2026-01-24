from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm
from django.forms import inlineformset_factory
from .models import Unit, Participant


class UserRegistrationForm(UserCreationForm):
    """
    Form for registering new users with additional fields.
    """
    first_name = forms.CharField(
        max_length=150,
        required=True,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'First Name'})
    )
    last_name = forms.CharField(
        max_length=150,
        required=True,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Last Name'})
    )
    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'Email'})
    )

    class Meta:
        model = User
        fields = ['username', 'first_name', 'last_name', 'email', 'password1', 'password2']
        widgets = {
            'username': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Username'}),
        }

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError('This email address is already registered.')
        return email


class UnitForm(forms.ModelForm):
    """
    Form for creating/editing a Unit.
    """
    expected_arrival = forms.DateTimeField(
        required=False,
        widget=forms.DateTimeInput(attrs={
            'class': 'form-control',
            'type': 'datetime-local',
            'placeholder': 'YYYY-MM-DD HH:MM'
        }),
        help_text='Expected date and time of arrival'
    )
    
    expected_departure = forms.DateTimeField(
        required=False,
        widget=forms.DateTimeInput(attrs={
            'class': 'form-control',
            'type': 'datetime-local',
            'placeholder': 'YYYY-MM-DD HH:MM'
        }),
        help_text='Expected date and time of departure'
    )
    
    class Meta:
        model = Unit
        fields = ['unit_name', 'unit_evidence_id', 'contact_person_name', 'contact_email', 
                  'contact_phone', 'backup_contact_phone', 'relevant_information',
                  'expected_arrival', 'expected_departure', 'home_town',
                  'boats_p550', 'boats_sail', 'boats_paddle', 'boats_motor',
                  'accommodation_expectations', 'estimated_accommodation_area', 'wishes_notes']
        widgets = {
            'unit_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Unit Name'}),
            'unit_evidence_id': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g., 523.10, 816.08.001'}),
            'contact_person_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Contact Person Name'}),
            'contact_email': forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'Contact Email'}),
            'contact_phone': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Contact Phone'}),
            'backup_contact_phone': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Backup Phone (optional)'}),
            'relevant_information': forms.Textarea(attrs={'class': 'form-control', 'placeholder': 'Relevant information', 'rows': 3}),
            'home_town': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Home Town'}),
            'boats_p550': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': '0', 'min': '0'}),
            'boats_sail': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': '0', 'min': '0'}),
            'boats_paddle': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': '0', 'min': '0'}),
            'boats_motor': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': '0', 'min': '0'}),
            'accommodation_expectations': forms.Textarea(attrs={'class': 'form-control', 'placeholder': 'Accommodation expectations', 'rows': 3}),
            'estimated_accommodation_area': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g., 100 m²'}),
            'wishes_notes': forms.Textarea(attrs={'class': 'form-control', 'placeholder': 'Wishes, notes, etc.', 'rows': 3}),
        }


class ParticipantForm(forms.ModelForm):
    """
    Form for creating/editing a Participant.
    """
    date_of_birth = forms.DateField(
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date',
            'placeholder': 'YYYY-MM-DD'
        }),
        help_text='Date of birth'
    )
    
    class Meta:
        model = Participant
        fields = ['first_name', 'last_name', 'nickname', 'date_of_birth', 'category', 'health_restrictions', 'dietary_restrictions', 'relevant_information']
        widgets = {
            'first_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'First Name'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Last Name'}),
            'nickname': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nickname (optional)'}),
            'category': forms.Select(attrs={'class': 'form-control'}),
            'health_restrictions': forms.Textarea(attrs={'class': 'form-control', 'placeholder': 'Health restrictions (optional)', 'rows': 2}),
            'dietary_restrictions': forms.Textarea(attrs={'class': 'form-control', 'placeholder': 'Dietary restrictions (optional)', 'rows': 2}),
            'relevant_information': forms.Textarea(attrs={'class': 'form-control', 'placeholder': 'Relevant information (optional)', 'rows': 2}),
        }


# Formset for adding multiple participants to a unit
ParticipantFormSet = inlineformset_factory(
    Unit,
    Participant,
    form=ParticipantForm,
    extra=3,  # Number of empty forms to display
    can_delete=True,
    min_num=0,
    validate_min=False,
)
