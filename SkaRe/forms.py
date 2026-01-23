from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm
from django.forms import inlineformset_factory
from .models import Group, Participant


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


class GroupForm(forms.ModelForm):
    """
    Form for creating/editing a Group.
    """
    class Meta:
        model = Group
        fields = ['name', 'description']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Group Name'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'placeholder': 'Description', 'rows': 3}),
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
        fields = ['first_name', 'last_name', 'nickname', 'date_of_birth', 'health_restrictions', 'dietary_restrictions']
        widgets = {
            'first_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'First Name'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Last Name'}),
            'nickname': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nickname (optional)'}),
            'health_restrictions': forms.Textarea(attrs={'class': 'form-control', 'placeholder': 'Health restrictions (optional)', 'rows': 2}),
            'dietary_restrictions': forms.Textarea(attrs={'class': 'form-control', 'placeholder': 'Dietary restrictions (optional)', 'rows': 2}),
        }


# Formset for adding multiple participants to a group
ParticipantFormSet = inlineformset_factory(
    Group,
    Participant,
    form=ParticipantForm,
    extra=3,  # Number of empty forms to display
    can_delete=True,
    min_num=0,
    validate_min=False,
)
