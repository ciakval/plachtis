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


class IndividualForm(forms.Form):
    """
    Form for creating/editing an Individual (a Unit with one Participant).
    Combines necessary fields from both Unit and Participant models.
    """
    # Unit fields (simplified for individual registration)
    unit_name = forms.CharField(
        max_length=200,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Unit Name (optional)'}),
        required=False,
        help_text='If not provided, will be auto-generated from participant name'
    )
    unit_evidence_id = forms.CharField(
        max_length=50,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g., 523.10, 816.08.001'}),
        help_text='Unit evidence ID'
    )
    contact_email = forms.EmailField(
        widget=forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'Contact Email'}),
        help_text='Contact email address'
    )
    contact_phone = forms.CharField(
        max_length=20,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Contact Phone'}),
        help_text='Contact phone number'
    )
    backup_contact_phone = forms.CharField(
        max_length=20,
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Backup Phone (optional)'}),
        help_text='Optional backup contact phone'
    )
    
    # Event logistics fields
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
    
    home_town = forms.CharField(
        max_length=200,
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Home Town'}),
        help_text='Home town'
    )
    
    # Accommodation fields
    accommodation_expectations = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={'class': 'form-control', 'placeholder': 'Accommodation expectations', 'rows': 2}),
        help_text='Accommodation expectations'
    )
    
    wishes_notes = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={'class': 'form-control', 'placeholder': 'Wishes, notes, etc.', 'rows': 2}),
        help_text='Wishes, notes, etc.'
    )
    
    # Participant fields
    first_name = forms.CharField(
        max_length=100,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'First Name'}),
        help_text='First name'
    )
    last_name = forms.CharField(
        max_length=100,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Last Name'}),
        help_text='Last name'
    )
    nickname = forms.CharField(
        max_length=100,
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nickname (optional)'}),
        help_text='Optional nickname'
    )
    date_of_birth = forms.DateField(
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date',
            'placeholder': 'YYYY-MM-DD'
        }),
        help_text='Date of birth'
    )
    category = forms.ChoiceField(
        choices=Participant.ScoutCategory.choices,
        widget=forms.Select(attrs={'class': 'form-control'}),
        help_text='Scout category'
    )
    health_restrictions = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={'class': 'form-control', 'placeholder': 'Health restrictions (optional)', 'rows': 2}),
        help_text='Any health restrictions or medical conditions'
    )
    dietary_restrictions = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={'class': 'form-control', 'placeholder': 'Dietary restrictions (optional)', 'rows': 2}),
        help_text='Any dietary restrictions or preferences'
    )
    relevant_information = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={'class': 'form-control', 'placeholder': 'Relevant information (optional)', 'rows': 2}),
        help_text='Any relevant information about the participant'
    )
    
    def save(self, unit_instance=None, user=None):
        """
        Save the form data to create or update a Unit and its associated Participant.
        """
        # Extract cleaned data
        unit_name = self.cleaned_data.get('unit_name')
        if not unit_name:
            # Auto-generate unit name from participant name
            first_name = self.cleaned_data.get('first_name')
            last_name = self.cleaned_data.get('last_name')
            unit_name = f"{first_name} {last_name}"
        
        # Prepare unit data
        unit_data = {
            'is_individual': True,
            'unit_name': unit_name,
            'unit_evidence_id': self.cleaned_data.get('unit_evidence_id'),
            'contact_person_name': f"{self.cleaned_data.get('first_name')} {self.cleaned_data.get('last_name')}",
            'contact_email': self.cleaned_data.get('contact_email'),
            'contact_phone': self.cleaned_data.get('contact_phone'),
            'backup_contact_phone': self.cleaned_data.get('backup_contact_phone', ''),
            'expected_arrival': self.cleaned_data.get('expected_arrival'),
            'expected_departure': self.cleaned_data.get('expected_departure'),
            'home_town': self.cleaned_data.get('home_town', ''),
            'accommodation_expectations': self.cleaned_data.get('accommodation_expectations', ''),
            'wishes_notes': self.cleaned_data.get('wishes_notes', ''),
            # Set boat counts to 0 for individuals
            'boats_p550': 0,
            'boats_sail': 0,
            'boats_paddle': 0,
            'boats_motor': 0,
            'estimated_accommodation_area': '',
            'relevant_information': '',
        }
        
        # Create or update Unit
        if unit_instance:
            for key, value in unit_data.items():
                setattr(unit_instance, key, value)
            unit_instance.save()
            unit = unit_instance
        else:
            if user:
                unit_data['created_by'] = user
            unit = Unit.objects.create(**unit_data)
        
        # Prepare participant data
        participant_data = {
            'first_name': self.cleaned_data.get('first_name'),
            'last_name': self.cleaned_data.get('last_name'),
            'nickname': self.cleaned_data.get('nickname', ''),
            'date_of_birth': self.cleaned_data.get('date_of_birth'),
            'category': self.cleaned_data.get('category'),
            'health_restrictions': self.cleaned_data.get('health_restrictions', ''),
            'dietary_restrictions': self.cleaned_data.get('dietary_restrictions', ''),
            'relevant_information': self.cleaned_data.get('relevant_information', ''),
        }
        
        # Create or update Participant
        if unit_instance:
            # For editing, update the existing participant
            participant = unit.participants.first()
            if participant:
                for key, value in participant_data.items():
                    setattr(participant, key, value)
                participant.save()
            else:
                # Create new participant if none exists
                Participant.objects.create(unit=unit, **participant_data)
        else:
            # For creating, add new participant
            Participant.objects.create(unit=unit, **participant_data)
        
        return unit
