from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db import transaction
from django import forms
from .forms import UserRegistrationForm, UnitRegistrationForm, RegularParticipantFormSet
from .models import Entity, Unit, RegularParticipant, EventSettings


def home(request):
    """Homepage view."""
    return render(request, 'SkaRe/home.html')


def user_login(request):
    """User login view."""
    if request.user.is_authenticated:
        return redirect('SkaRe:home')
    
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)
        
        if user is not None:
            login(request, user)
            messages.success(request, f'Welcome back, {user.first_name or user.username}!')
            next_url = request.GET.get('next', 'SkaRe:home')
            return redirect(next_url)
        else:
            messages.error(request, 'Invalid username or password.')
    
    form = AuthenticationForm()
    return render(request, 'SkaRe/login.html', {'form': form})


def user_logout(request):
    """User logout view."""
    logout(request)
    messages.success(request, 'You have been logged out successfully.')
    return redirect('SkaRe:login')


def user_register(request):
    """User registration view."""
    if request.user.is_authenticated:
        return redirect('SkaRe:home')
    
    if request.method == 'POST':
        form = UserRegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, f'Welcome, {user.first_name}! Your account has been created successfully.')
            return redirect('SkaRe:home')
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = UserRegistrationForm()
    
    return render(request, 'SkaRe/register.html', {'form': form})


@login_required
def register_unit(request):
    """View for registering a new Unit with participants."""
    
    # Check if registration is still open
    if not EventSettings.is_registration_open():
        messages.error(request, 'Registration is currently closed.')
        return redirect('SkaRe:home')
    
    if request.method == 'POST':
        unit_form = UnitRegistrationForm(request.POST)
        participant_formset = RegularParticipantFormSet(request.POST, prefix='participants')
        
        if unit_form.is_valid() and participant_formset.is_valid():
            try:
                with transaction.atomic():
                    # Create Entity with scout unit fields
                    entity = Entity.objects.create(
                        created_by=request.user,
                        scout_unit_name=unit_form.cleaned_data['scout_unit_name'],
                        scout_unit_evidence_id=unit_form.cleaned_data['scout_unit_evidence_id'],
                        contact_email=unit_form.cleaned_data['contact_email'],
                        contact_phone=unit_form.cleaned_data['contact_phone'],
                        expected_arrival=unit_form.cleaned_data.get('expected_arrival'),
                        expected_departure=unit_form.cleaned_data.get('expected_departure'),
                        home_town=unit_form.cleaned_data.get('home_town', '')
                    )
                    
                    # Create Unit
                    unit = unit_form.save(commit=False)
                    unit.entity = entity
                    unit.save()
                    
                    # Create participants
                    participant_count = 0
                    for form in participant_formset:
                        if form.cleaned_data and not form.cleaned_data.get('DELETE', False):
                            participant = form.save(commit=False)
                            participant.unit = unit
                            participant.save()
                            participant_count += 1
                    
                    messages.success(
                        request,
                        f'Unit "{entity.scout_unit_name}" registered successfully with {participant_count} participant(s)!'
                    )
                    return redirect('SkaRe:home')
                    
            except Exception as e:
                messages.error(request, f'Error registering unit: {str(e)}')
        else:
            messages.error(request, 'Please correct the errors in the form.')
    else:
        unit_form = UnitRegistrationForm()
        participant_formset = RegularParticipantFormSet(prefix='participants')
    
    context = {
        'unit_form': unit_form,
        'participant_formset': participant_formset,
        'deadline': EventSettings.get_deadline(),
    }
    return render(request, 'SkaRe/register_unit.html', context)


@login_required
def list_units(request):
    """View for listing units created by the current user."""
    # Get all entities created by the user that have a Unit associated
    units = Unit.objects.filter(entity__created_by=request.user).select_related(
        'entity'
    ).prefetch_related('regular_participants')
    
    context = {
        'units': units,
    }
    return render(request, 'SkaRe/list_units.html', context)


@login_required
def edit_unit(request, unit_id):
    """View for editing an existing Unit."""
    unit = get_object_or_404(Unit, id=unit_id)
    
    # Check if user owns this unit
    if unit.entity.created_by != request.user:
        messages.error(request, 'You do not have permission to edit this unit.')
        return redirect('SkaRe:list_units')
    
    # Check if unit can be edited
    if not unit.entity.can_be_edited(request.user):
        messages.error(request, 'This unit cannot be edited after the registration deadline.')
        return redirect('SkaRe:list_units')
    
    # Define forms inline
    class UnitEditForm(forms.ModelForm):
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
                'backup_contact_phone': forms.TextInput(attrs={'class': 'form-control'}),
                'boats_p550': forms.NumberInput(attrs={'class': 'form-control', 'min': '0'}),
                'boats_sail': forms.NumberInput(attrs={'class': 'form-control', 'min': '0'}),
                'boats_paddle': forms.NumberInput(attrs={'class': 'form-control', 'min': '0'}),
                'boats_motor': forms.NumberInput(attrs={'class': 'form-control', 'min': '0'}),
                'accommodation_expectations': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
                'estimated_accommodation_area': forms.TextInput(attrs={'class': 'form-control'}),
            }
    
    class EntityEditForm(forms.ModelForm):
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
            model = Entity
            fields = ['scout_unit_name', 'scout_unit_evidence_id', 'contact_email', 'contact_phone', 'expected_arrival', 'expected_departure', 'home_town']
            widgets = {
                'scout_unit_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g., 5. oddíl Koráb'}),
                'scout_unit_evidence_id': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g., 523.10'}),
                'contact_email': forms.EmailInput(attrs={'class': 'form-control'}),
                'contact_phone': forms.TextInput(attrs={'class': 'form-control'}),
                'expected_arrival': forms.DateTimeInput(attrs={'class': 'form-control', 'type': 'datetime-local'}),
                'expected_departure': forms.DateTimeInput(attrs={'class': 'form-control', 'type': 'datetime-local'}),
                'home_town': forms.TextInput(attrs={'class': 'form-control'}),
            }
    
    # Get existing participants
    existing_participants = RegularParticipant.objects.filter(unit=unit)
    
    if request.method == 'POST':
        unit_form = UnitEditForm(request.POST, instance=unit)
        entity_form = EntityEditForm(request.POST, instance=unit.entity)
        participant_formset = RegularParticipantFormSet(request.POST, prefix='participants')
        
        if unit_form.is_valid() and entity_form.is_valid() and participant_formset.is_valid():
            try:
                with transaction.atomic():
                    # Save entity and unit
                    entity_form.save()
                    unit_form.save()
                    
                    # Delete all existing participants and recreate from form
                    # This avoids issues with multi-table inheritance updates
                    existing_participants.delete()
                    
                    # Create all participants from formset
                    participant_count = 0
                    for form in participant_formset:
                        if form.cleaned_data and not form.cleaned_data.get('DELETE', False):
                            participant = form.save(commit=False)
                            participant.unit = unit
                            participant.save()
                            participant_count += 1
                    
                    messages.success(request, f'Unit "{unit.entity.scout_unit_name}" updated successfully with {participant_count} participant(s)!')
                    return redirect('SkaRe:list_units')
            except Exception as e:
                messages.error(request, f'Error updating unit: {str(e)}')
        else:
            messages.error(request, 'Please correct the errors in the form.')
    else:
        unit_form = UnitEditForm(instance=unit)
        entity_form = EntityEditForm(instance=unit.entity)
        
        # Pre-fill formset with existing participants
        initial_data = []
        for participant in existing_participants:
            initial_data.append({
                'first_name': participant.first_name,
                'last_name': participant.last_name,
                'nickname': participant.nickname,
                'date_of_birth': participant.date_of_birth,
                'category': participant.category,
                'health_restrictions': participant.health_restrictions,
                'dietary_restrictions': participant.dietary_restrictions,
                'relevant_information': participant.relevant_information,
            })
        
        participant_formset = RegularParticipantFormSet(
            prefix='participants',
            initial=initial_data
        )
    
    context = {
        'unit': unit,
        'unit_form': unit_form,
        'entity_form': entity_form,
        'participant_formset': participant_formset,
        'existing_participants': existing_participants,
    }
    return render(request, 'SkaRe/edit_unit.html', context)
