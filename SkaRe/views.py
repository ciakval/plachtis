import csv
import io
import urllib.request

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib import messages
from django.conf import settings
from django.core.cache import cache
from django.db import IntegrityError, transaction
from django.db.models import Q, Sum
from django.core.paginator import Paginator
from django import forms
from django.utils.translation import gettext as _
from django.utils.http import url_has_allowed_host_and_scheme
from django.http import HttpResponse, JsonResponse
from .forms import (
    UserRegistrationForm, UnitRegistrationForm,
    IndividualParticipantRegistrationForm, OrganizerRegistrationForm,
    validate_czech_phone, get_participant_formset, BoatForm, CrewRegistrationForm
)
from .form_utils import generate_form_token, is_duplicate_submission, consume_form_token
from .models import (
    Entity, Unit, RegularParticipant, EventSettings,
    IndividualParticipant, Organizer, BoatClass, Boat,
    Person, Crew, CrewMember
)


ADMIN_RESULTS_LIMIT = 500
MANAGE_ENTITIES_PAGE_SIZE = 100



def home(request):
    """Homepage view."""
    context = {
        'registration_deadline': EventSettings.get_registration_deadline(),
        'editing_deadline': EventSettings.get_editing_deadline(),
    }
    return render(request, 'SkaRe/home.html', context)


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
            messages.success(request, _('Welcome back, {name}!').format(name=user.first_name or user.username))
            next_url = request.GET.get('next', 'SkaRe:home')
            
            # Validate next_url to prevent open redirect vulnerability
            # URL names (like 'SkaRe:home') are safe to use directly
            # For actual URLs (absolute or relative), validate they're allowed
            if '://' in next_url or next_url.startswith('/'):
                # It's an actual URL (absolute or relative), validate it
                if not url_has_allowed_host_and_scheme(next_url, allowed_hosts=None):
                    next_url = 'SkaRe:home'
            
            return redirect(next_url)
        else:
            messages.error(request, _('Invalid username or password.'))
    
    form = AuthenticationForm()
    return render(request, 'SkaRe/login.html', {'form': form})


def user_logout(request):
    """User logout view."""
    logout(request)
    messages.success(request, _('You have been logged out successfully.'))
    return redirect('SkaRe:login')


def forgot_password(request):
    """View for forgot password page."""
    return render(request, 'SkaRe/forgot_password.html')


def user_register(request):
    """User registration view."""
    if request.user.is_authenticated:
        return redirect('SkaRe:home')
    
    if request.method == 'POST':
        if is_duplicate_submission(request):
            messages.warning(request, _('This form was already submitted.'))
            return redirect('SkaRe:home')
        form = UserRegistrationForm(request.POST)
        if form.is_valid():
            consume_form_token(request)  # Consume token only after successful validation
            user = form.save()
            login(request, user)
            messages.success(request, _('Welcome, {name}! Your account has been created successfully.').format(name=user.first_name))
            return redirect('SkaRe:home')
        else:
            messages.error(request, _('Please correct the errors below.'))
    else:
        form = UserRegistrationForm()
        form_token = generate_form_token(request)
    
    return render(request, 'SkaRe/register.html', {'form': form, 'form_token': request.session.get('form_token', '')})


@login_required
def register_unit(request):
    """View for registering a new Unit with participants."""
    
    # Check if registration is still open
    if not EventSettings.is_registration_open():
        messages.error(request, _('Registration is currently closed.'))
        return redirect('SkaRe:home')
    
    if request.method == 'POST':
        if is_duplicate_submission(request):
            messages.warning(request, _('This form was already submitted.'))
            return redirect('SkaRe:home')
        unit_form = UnitRegistrationForm(request.POST)
        participant_formset = get_participant_formset(extra=3)(request.POST, prefix='participants', queryset=RegularParticipant.objects.none())
        
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
                        # Skip empty forms and deleted forms
                        if (form.cleaned_data and 
                            not form.cleaned_data.get('DELETE', False) and
                            form.has_data()):
                            participant = form.save(commit=False)
                            participant.unit = unit
                            participant.save()
                            participant_count += 1
                    
                    consume_form_token(request)  # Consume token only after successful processing
                    messages.success(
                        request,
                        _('Unit "{unit_name}" registered successfully with {count} participant(s)!').format(
                            unit_name=entity.scout_unit_name,
                            count=participant_count
                        )
                    )
                    return redirect('SkaRe:home')
                    
            except Exception as e:
                messages.error(request, _('Error registering unit: {error}').format(error=str(e)))
        else:
            messages.error(request, _('Please correct the errors in the form.'))
    else:
        unit_form = UnitRegistrationForm()
        participant_formset = get_participant_formset(extra=3)(prefix='participants', queryset=RegularParticipant.objects.none())
        generate_form_token(request)
    
    context = {
        'unit_form': unit_form,
        'participant_formset': participant_formset,
        'deadline': EventSettings.get_registration_deadline(),
        'form_token': request.session.get('form_token', ''),
    }
    return render(request, 'SkaRe/register_unit.html', context)


@login_required
def list_units(request):
    """View for listing units owned by or editable by the current user."""
    
    # Get units where user is owner or editor
    units = Unit.objects.filter(
        Q(entity__created_by=request.user) | Q(entity__editors=request.user)
    ).select_related('entity').prefetch_related('regular_participants', 'entity__editors').distinct()
    
    context = {
        'units': units,
        'editing_deadline': EventSettings.get_editing_deadline(),
    }
    return render(request, 'SkaRe/list_units.html', context)


@login_required
def edit_unit(request, unit_id):
    """View for editing an existing Unit."""
    unit = get_object_or_404(Unit, id=unit_id)
    
    # Check if user has permission to edit this unit (owner or editor)
    is_owner = unit.entity.created_by == request.user
    is_editor = unit.entity.editors.filter(id=request.user.id).exists()
    if not (is_owner or is_editor):
        messages.error(request, _('You do not have permission to edit this unit.'))
        return redirect('SkaRe:list_units')
    
    # Check if unit can be edited
    if not unit.entity.can_be_edited(request.user):
        messages.error(request, _('This unit cannot be edited after the editing deadline.'))
        return redirect('SkaRe:list_units')
    
    # Define forms inline
    class UnitEditForm(forms.ModelForm):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            # Add 'is-invalid' class to fields with errors (after form is bound and validated)
            if self.is_bound:
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
                'backup_contact_phone': forms.TextInput(attrs={'class': 'form-control'}),
                'boats_p550': forms.NumberInput(attrs={'class': 'form-control', 'min': '0'}),
                'boats_sail': forms.NumberInput(attrs={'class': 'form-control', 'min': '0'}),
                'boats_paddle': forms.NumberInput(attrs={'class': 'form-control', 'min': '0'}),
                'boats_motor': forms.NumberInput(attrs={'class': 'form-control', 'min': '0'}),
                'scarf_count': forms.NumberInput(attrs={'class': 'form-control', 'min': '0'}),
                'hat_count': forms.NumberInput(attrs={'class': 'form-control', 'min': '0'}),
                'accommodation_expectations': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
                'estimated_accommodation_area': forms.TextInput(attrs={'class': 'form-control'}),
            }
    
    class EntityEditForm(forms.ModelForm):
        # Explicitly define required fields to match registration form
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
        
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            # Add phone validator to contact_phone field
            if 'contact_phone' in self.fields:
                self.fields['contact_phone'].validators.append(validate_czech_phone)
            # Add 'is-invalid' class to fields with errors (after form is bound and validated)
            if self.is_bound:
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
                'contact_email': forms.EmailInput(attrs={'class': 'form-control'}),
                'contact_phone': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '+420 123 456 789'}),
                'expected_arrival': forms.DateTimeInput(attrs={'class': 'form-control', 'type': 'datetime-local'}, format='%Y-%m-%dT%H:%M'),
                'expected_departure': forms.DateTimeInput(attrs={'class': 'form-control', 'type': 'datetime-local'}, format='%Y-%m-%dT%H:%M'),
                'home_town': forms.TextInput(attrs={'class': 'form-control'}),
            }
    
    # Get existing participants
    existing_participants = RegularParticipant.objects.filter(unit=unit)
    
    if request.method == 'POST':
        unit_form = UnitEditForm(request.POST, instance=unit)
        entity_form = EntityEditForm(request.POST, instance=unit.entity)
        participant_formset = get_participant_formset(extra=0)(
            request.POST,
            prefix='participants',
            queryset=existing_participants
        )
        
        unit_valid = unit_form.is_valid()
        entity_valid = entity_form.is_valid()
        formset_valid = participant_formset.is_valid()
        
        if unit_valid and entity_valid and formset_valid:
            try:
                with transaction.atomic():
                    entity_form.save()
                    unit_form.save()
                    
                    instances = participant_formset.save(commit=False)
                    for instance in instances:
                        instance.unit = unit
                        instance.save()
                    
                    for form in participant_formset.deleted_forms:
                        if form.instance and form.instance.pk:
                            form.instance.delete()
                    
                    participant_count = len(instances)
                    messages.success(request, _('Unit "{unit_name}" updated successfully with {count} participant(s)!').format(
                        unit_name=unit.entity.scout_unit_name,
                        count=participant_count
                    ))
                    return redirect('SkaRe:list_units')
            except Exception as e:
                messages.error(request, _('Error updating unit: {error}').format(error=str(e)))
        else:
            if not unit_valid or not entity_valid:
                if not formset_valid:
                    messages.error(request, _('Please correct the errors in the form of unit and participants'))
                else:
                    messages.error(request, _('Please correct the errors in the form of unit'))
            elif not formset_valid:
                messages.error(request, _('Please correct the errors in the form of participants'))
            else:
                messages.error(request, _('Please correct the errors in the form.'))
    else:
        unit_form = UnitEditForm(instance=unit)
        entity_form = EntityEditForm(instance=unit.entity)
        participant_formset = get_participant_formset(extra=0)(
            prefix='participants',
            queryset=existing_participants
        )
    
    context = {
        'unit': unit,
        'unit_form': unit_form,
        'entity_form': entity_form,
        'participant_formset': participant_formset,
        'existing_participants': list(existing_participants),
    }
    return render(request, 'SkaRe/edit_unit.html', context)


@login_required
def register_individual_participant(request):
    """View for registering a new Individual Participant."""
    
    # Check if registration is still open
    if not EventSettings.is_registration_open():
        messages.error(request, _('Registration is currently closed.'))
        return redirect('SkaRe:home')
    
    if request.method == 'POST':
        if is_duplicate_submission(request):
            messages.warning(request, _('This form was already submitted.'))
            return redirect('SkaRe:home')
        form = IndividualParticipantRegistrationForm(request.POST)
        
        if form.is_valid():
            try:
                with transaction.atomic():
                    # Create Entity
                    entity = Entity.objects.create(
                        created_by=request.user,
                        contact_email=form.cleaned_data['contact_email'],
                        contact_phone=form.cleaned_data['contact_phone'],
                        expected_arrival=form.cleaned_data.get('expected_arrival'),
                        expected_departure=form.cleaned_data.get('expected_departure'),
                        home_town=form.cleaned_data.get('home_town', '')
                    )
                    
                    # Create Individual Participant
                    participant = form.save(commit=False)
                    participant.entity = entity
                    participant.save()
                    
                    consume_form_token(request)  # Consume token only after successful processing
                    messages.success(
                        request,
                        _('Individual Participant "{name}" registered successfully!').format(name=str(participant))
                    )
                    return redirect('SkaRe:home')
                    
            except Exception as e:
                messages.error(request, _('Error registering individual participant: {error}').format(error=str(e)))
        else:
            messages.error(request, _('Please correct the errors in the form.'))
    else:
        form = IndividualParticipantRegistrationForm()
        generate_form_token(request)
    
    context = {
        'form': form,
        'deadline': EventSettings.get_registration_deadline(),
        'form_token': request.session.get('form_token', ''),
    }
    return render(request, 'SkaRe/register_individual_participant.html', context)


@login_required
def list_individual_participants(request):
    """View for listing individual participants owned by or editable by the current user."""   
    participants = IndividualParticipant.objects.filter(
        Q(entity__created_by=request.user) | Q(entity__editors=request.user)
    ).select_related('entity').prefetch_related('entity__editors').distinct()
    
    context = {
        'participants': participants,
        'editing_deadline': EventSettings.get_editing_deadline(),
    }
    return render(request, 'SkaRe/list_individual_participants.html', context)


@login_required
def edit_individual_participant(request, participant_id):
    """View for editing an existing Individual Participant."""
    participant = get_object_or_404(IndividualParticipant, id=participant_id)
    
    # Check if user has permission to edit this participant (owner or editor)
    is_owner = participant.entity.created_by == request.user
    is_editor = participant.entity.editors.filter(id=request.user.id).exists()
    if not (is_owner or is_editor):
        messages.error(request, _('You do not have permission to edit this participant.'))
        return redirect('SkaRe:list_individual_participants')
    
    # Check if participant can be edited
    if not participant.entity.can_be_edited(request.user):
        messages.error(request, _('This participant cannot be edited after the editing deadline.'))
        return redirect('SkaRe:list_individual_participants')
    
    # Define forms inline
    class IndividualParticipantEditForm(forms.ModelForm):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
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
                'first_name': forms.TextInput(attrs={'class': 'form-control'}),
                'last_name': forms.TextInput(attrs={'class': 'form-control'}),
                'nickname': forms.TextInput(attrs={'class': 'form-control'}),
                'date_of_birth': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}, format='%Y-%m-%d'),
                'category': forms.Select(attrs={'class': 'form-control'}),
                'health_restrictions': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
                'dietary_restrictions': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
                'relevant_information': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
                'boats_p550': forms.NumberInput(attrs={'class': 'form-control', 'min': '0'}),
                'boats_sail': forms.NumberInput(attrs={'class': 'form-control', 'min': '0'}),
                'boats_paddle': forms.NumberInput(attrs={'class': 'form-control', 'min': '0'}),
                'boats_motor': forms.NumberInput(attrs={'class': 'form-control', 'min': '0'}),
                'scarf_count': forms.NumberInput(attrs={'class': 'form-control', 'min': '0'}),
                'hat_count': forms.NumberInput(attrs={'class': 'form-control', 'min': '0'}),
                'accommodation_expectations': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
                'estimated_accommodation_area': forms.TextInput(attrs={'class': 'form-control'}),
            }
    
    class EntityEditForm(forms.ModelForm):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            # Add phone validator to contact_phone field
            if 'contact_phone' in self.fields:
                self.fields['contact_phone'].validators.append(validate_czech_phone)
            for field_name, field in self.fields.items():
                if field_name in self.errors:
                    if 'class' in field.widget.attrs:
                        field.widget.attrs['class'] += ' is-invalid'
                    else:
                        field.widget.attrs['class'] = 'is-invalid'
        
        class Meta:
            model = Entity
            fields = ['contact_email', 'contact_phone', 'expected_arrival', 'expected_departure', 'home_town']
            widgets = {
                'contact_email': forms.EmailInput(attrs={'class': 'form-control'}),
                'contact_phone': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '+420 123 456 789'}),
                'expected_arrival': forms.DateTimeInput(attrs={'class': 'form-control', 'type': 'datetime-local'}, format='%Y-%m-%dT%H:%M'),
                'expected_departure': forms.DateTimeInput(attrs={'class': 'form-control', 'type': 'datetime-local'}, format='%Y-%m-%dT%H:%M'),
                'home_town': forms.TextInput(attrs={'class': 'form-control'}),
            }
    
    if request.method == 'POST':
        participant_form = IndividualParticipantEditForm(request.POST, instance=participant)
        entity_form = EntityEditForm(request.POST, instance=participant.entity)
        
        if participant_form.is_valid() and entity_form.is_valid():
            try:
                with transaction.atomic():
                    entity_form.save()
                    participant_form.save()
                    
                    messages.success(request, _('Individual Participant "{name}" updated successfully!').format(name=str(participant)))
                    return redirect('SkaRe:list_individual_participants')
            except Exception as e:
                messages.error(request, _('Error updating participant: {error}').format(error=str(e)))
        else:
            messages.error(request, _('Please correct the errors in the form.'))
    else:
        participant_form = IndividualParticipantEditForm(instance=participant)
        entity_form = EntityEditForm(instance=participant.entity)
    
    context = {
        'participant': participant,
        'participant_form': participant_form,
        'entity_form': entity_form,
    }
    return render(request, 'SkaRe/edit_individual_participant.html', context)


@login_required
def register_organizer(request):
    """View for registering a new Organizer."""
    
    # Check if registration is still open
    if not EventSettings.is_registration_open():
        messages.error(request, _('Registration is currently closed.'))
        return redirect('SkaRe:home')
    
    if request.method == 'POST':
        if is_duplicate_submission(request):
            messages.warning(request, _('This form was already submitted.'))
            return redirect('SkaRe:home')
        form = OrganizerRegistrationForm(request.POST)
        
        if form.is_valid():
            try:
                with transaction.atomic():
                    # Create Entity
                    entity = Entity.objects.create(
                        created_by=request.user,
                        contact_email=form.cleaned_data['contact_email'],
                        contact_phone=form.cleaned_data['contact_phone'],
                        expected_arrival=form.cleaned_data.get('expected_arrival'),
                        expected_departure=form.cleaned_data.get('expected_departure'),
                        home_town=form.cleaned_data.get('home_town', '')
                    )
                    
                    # Create Organizer
                    organizer = form.save(commit=False)
                    organizer.entity = entity
                    organizer.save()
                    
                    consume_form_token(request)  # Consume token only after successful processing
                    messages.success(
                        request,
                        _('Organizer "{name}" registered successfully!').format(name=str(organizer))
                    )
                    return redirect('SkaRe:home')
                    
            except Exception as e:
                messages.error(request, _('Error registering organizer: {error}').format(error=str(e)))
        else:
            messages.error(request, _('Please correct the errors in the form.'))
    else:
        form = OrganizerRegistrationForm()
        generate_form_token(request)
    
    context = {
        'form': form,
        'deadline': EventSettings.get_registration_deadline(),
        'form_token': request.session.get('form_token', ''),
    }
    return render(request, 'SkaRe/register_organizer.html', context)


@login_required
def list_organizers(request):
    """View for listing organizers owned by or editable by the current user."""   
    organizers = Organizer.objects.filter(
        Q(entity__created_by=request.user) | Q(entity__editors=request.user)
    ).select_related('entity').prefetch_related('entity__editors').distinct()
    
    context = {
        'organizers': organizers,
        'editing_deadline': EventSettings.get_editing_deadline(),
    }
    return render(request, 'SkaRe/list_organizers.html', context)


@login_required
def list_all(request):
    """View for listing all individual participants - staff only."""
    if not request.user.is_staff:
        messages.error(request, _('You do not have permission to view this page.'))
        return redirect('SkaRe:home')
    
    participant_total = IndividualParticipant.objects.count()
    organizer_total = Organizer.objects.count()
    regular_participant_total = RegularParticipant.objects.count()

    participants = IndividualParticipant.objects.select_related('entity').order_by('-id')[:ADMIN_RESULTS_LIMIT]
    organizers = Organizer.objects.select_related('entity').order_by('-id')[:ADMIN_RESULTS_LIMIT]
    units = Unit.objects.select_related('entity').order_by('-id')[:ADMIN_RESULTS_LIMIT]
    regular_participants = RegularParticipant.objects.select_related('unit', 'unit__entity').order_by('-id')[:ADMIN_RESULTS_LIMIT]

    results_limited = (
        participant_total > ADMIN_RESULTS_LIMIT
        or organizer_total > ADMIN_RESULTS_LIMIT
        or regular_participant_total > ADMIN_RESULTS_LIMIT
    )

    context = {
        'participants': participants,
        'organizers': organizers,
        'units': units,
        'regular_participants': regular_participants,
        'participant_total': participant_total,
        'organizer_total': organizer_total,
        'regular_participant_total': regular_participant_total,
        'results_limited': results_limited,
        'results_limit': ADMIN_RESULTS_LIMIT,
    }
    return render(request, 'SkaRe/list_all.html', context)


@login_required
def list_merchandise(request):
    """View for listing scarves and hats for units, individual participants, and organizers."""
    if not request.user.is_staff:
        messages.error(request, _('You do not have permission to view this page.'))
        return redirect('SkaRe:home')
    
    # Get filter parameters
    search_query = request.GET.get('search', '').strip()
    type_filter = request.GET.get('type', '').strip()
    
    # Initialize querysets based on type filter
    if type_filter == 'unit':
        units = Unit.objects.select_related('entity')
        individual_participants = IndividualParticipant.objects.none()
        organizers = Organizer.objects.none()
    elif type_filter == 'individual_participant':
        units = Unit.objects.none()
        individual_participants = IndividualParticipant.objects.select_related('entity')
        organizers = Organizer.objects.none()
    elif type_filter == 'organizer':
        units = Unit.objects.none()
        individual_participants = IndividualParticipant.objects.none()
        organizers = Organizer.objects.select_related('entity')
    else:
        # Get all units, individual participants, and organizers
        units = Unit.objects.select_related('entity')
        individual_participants = IndividualParticipant.objects.select_related('entity')
        organizers = Organizer.objects.select_related('entity')
    
    # Filter by name if search query is provided
    if search_query:
        # Filter units by scout_unit_name
        if type_filter == '' or type_filter == 'unit':
            units = units.filter(entity__scout_unit_name__icontains=search_query)
        # Filter individual participants by first_name or last_name
        if type_filter == '' or type_filter == 'individual_participant':
            individual_participants = individual_participants.filter(
                Q(first_name__icontains=search_query) | Q(last_name__icontains=search_query)
            )
        # Filter organizers by first_name or last_name
        if type_filter == '' or type_filter == 'organizer':
            organizers = organizers.filter(
                Q(first_name__icontains=search_query) | Q(last_name__icontains=search_query)
            )
    
    unit_total = units.count()
    individual_total = individual_participants.count()
    organizer_total = organizers.count()

    # Calculate totals from the full filtered querysets in SQL.
    total_scarves = sum(item or 0 for item in [
        units.aggregate(total=Sum('scarf_count'))['total'],
        individual_participants.aggregate(total=Sum('scarf_count'))['total'],
        organizers.filter(wants_scarf=True).count(),
    ])
    total_hats = sum(item or 0 for item in [
        units.aggregate(total=Sum('hat_count'))['total'],
        individual_participants.aggregate(total=Sum('hat_count'))['total'],
        organizers.filter(wants_hat=True).count(),
    ])

    results_limited = (
        unit_total > ADMIN_RESULTS_LIMIT
        or individual_total > ADMIN_RESULTS_LIMIT
        or organizer_total > ADMIN_RESULTS_LIMIT
    )

    # Guard against rendering massive tables in a single request.
    units = units.order_by('-id')[:ADMIN_RESULTS_LIMIT]
    individual_participants = individual_participants.order_by('-id')[:ADMIN_RESULTS_LIMIT]
    organizers = organizers.order_by('-id')[:ADMIN_RESULTS_LIMIT]
    
    context = {
        'units': units,
        'individual_participants': individual_participants,
        'organizers': organizers,
        'search_query': search_query,
        'type_filter': type_filter,
        'total_scarves': total_scarves,
        'total_hats': total_hats,
        'unit_total': unit_total,
        'individual_total': individual_total,
        'organizer_total': organizer_total,
        'results_limited': results_limited,
        'results_limit': ADMIN_RESULTS_LIMIT,
    }
    return render(request, 'SkaRe/list_merchandise.html', context)


@login_required
def edit_organizer(request, organizer_id):
    """View for editing an existing Organizer."""
    organizer = get_object_or_404(Organizer, id=organizer_id)
    
    # Check if user has permission to edit this organizer (owner or editor)
    is_owner = organizer.entity.created_by == request.user
    is_editor = organizer.entity.editors.filter(id=request.user.id).exists()
    if not (is_owner or is_editor):
        messages.error(request, _('You do not have permission to edit this organizer.'))
        return redirect('SkaRe:list_organizers')
    
    # Check if organizer can be edited
    if not organizer.entity.can_be_edited(request.user):
        messages.error(request, _('This organizer cannot be edited after the editing deadline.'))
        return redirect('SkaRe:list_organizers')
    
    # Define forms inline
    class OrganizerEditForm(forms.ModelForm):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
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
                'wants_scarf',
                'wants_hat',
            ]
            widgets = {
                'first_name': forms.TextInput(attrs={'class': 'form-control'}),
                'last_name': forms.TextInput(attrs={'class': 'form-control'}),
                'nickname': forms.TextInput(attrs={'class': 'form-control'}),
                'date_of_birth': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}, format='%Y-%m-%d'),
                'category': forms.Select(attrs={'class': 'form-control'}),
                'health_restrictions': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
                'dietary_restrictions': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
                'relevant_information': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
                'division': forms.Select(attrs={'class': 'form-control'}),
                'transport': forms.Select(attrs={'class': 'form-control'}),
                'need_lift': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
                'want_travel_order': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
                'accommodation': forms.Select(attrs={'class': 'form-control'}),
                'wants_scarf': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
                'wants_hat': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            }
    
    class EntityEditForm(forms.ModelForm):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            # Add phone validator to contact_phone field
            if 'contact_phone' in self.fields:
                self.fields['contact_phone'].validators.append(validate_czech_phone)
            for field_name, field in self.fields.items():
                if field_name in self.errors:
                    if 'class' in field.widget.attrs:
                        field.widget.attrs['class'] += ' is-invalid'
                    else:
                        field.widget.attrs['class'] = 'is-invalid'
        
        class Meta:
            model = Entity
            fields = ['contact_email', 'contact_phone', 'expected_arrival', 'expected_departure', 'home_town']
            widgets = {
                'contact_email': forms.EmailInput(attrs={'class': 'form-control'}),
                'contact_phone': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '+420 123 456 789'}),
                'expected_arrival': forms.DateTimeInput(attrs={'class': 'form-control', 'type': 'datetime-local'}, format='%Y-%m-%dT%H:%M'),
                'expected_departure': forms.DateTimeInput(attrs={'class': 'form-control', 'type': 'datetime-local'}, format='%Y-%m-%dT%H:%M'),
                'home_town': forms.TextInput(attrs={'class': 'form-control'}),
            }
    
    if request.method == 'POST':
        organizer_form = OrganizerEditForm(request.POST, instance=organizer)
        entity_form = EntityEditForm(request.POST, instance=organizer.entity)
        
        if organizer_form.is_valid() and entity_form.is_valid():
            try:
                with transaction.atomic():
                    entity_form.save()
                    organizer_form.save()
                    
                    messages.success(request, _('Organizer "{name}" updated successfully!').format(name=str(organizer)))
                    return redirect('SkaRe:list_organizers')
            except Exception as e:
                messages.error(request, _('Error updating organizer: {error}').format(error=str(e)))
        else:
            messages.error(request, _('Please correct the errors in the form.'))
    else:
        organizer_form = OrganizerEditForm(instance=organizer)
        entity_form = EntityEditForm(instance=organizer.entity)
    
    context = {
        'organizer': organizer,
        'organizer_form': organizer_form,
        'entity_form': entity_form,
    }
    return render(request, 'SkaRe/edit_organizer.html', context)


@login_required
def manage_entities(request):
    """Admin view for managing entity payment and confirmation status."""
    if not request.user.is_staff:
        messages.error(request, _('You do not have permission to view this page.'))
        return redirect('SkaRe:home')
    
    # Handle form submission
    if request.method == 'POST':
        # Get all entity IDs from the form
        entity_ids = request.POST.getlist('entity_ids')
        paid_entities = set(request.POST.getlist('paid'))
        confirmed_entities = set(request.POST.getlist('confirmed'))
        
        updated_count = 0
        try:
            for entity_id in entity_ids:
                try:
                    entity = Entity.objects.get(id=entity_id)
                    entity_updated = False
                    
                    # Update paid status
                    should_be_paid = entity_id in paid_entities
                    if entity.paid != should_be_paid:
                        entity.paid = should_be_paid
                        entity_updated = True
                    
                    # Update confirmed status
                    should_be_confirmed = entity_id in confirmed_entities
                    if entity.confirmed != should_be_confirmed:
                        entity.confirmed = should_be_confirmed
                        entity_updated = True
                    
                    if entity_updated:
                        entity.save()
                        updated_count += 1
                except Entity.DoesNotExist:
                    continue
            
            if updated_count > 0:
                messages.success(request, _('Updated {count} entities.').format(count=updated_count))
            else:
                messages.info(request, _('No changes made.'))
        except Exception as e:
            messages.error(request, _('Error updating entities: {error}').format(error=str(e)))
        
        # Preserve filter parameters
        from django.http import HttpResponseRedirect
        from django.urls import reverse
        from urllib.parse import urlencode
        
        params = {}
        for key in ['search', 'type', 'status', 'page']:
            value = request.POST.get(key, '').strip()
            if value:
                params[key] = value
        
        url = reverse('SkaRe:manage_entities')
        if params:
            url += '?' + urlencode(params)
        
        return HttpResponseRedirect(url)
    
    # Get filter parameters
    search_query = request.GET.get('search', '').strip()
    type_filter = request.GET.get('type', '').strip()
    status_filter = request.GET.get('status', '').strip()  # 'paid', 'unpaid', 'confirmed', 'unconfirmed', 'all'
    page_number = request.GET.get('page', '1')
    
    entities_qs = Entity.objects.select_related(
        'created_by',
        'unit_profile',
        'individual_participant_profile',
        'organizer_profile',
    )

    # Filter by type
    if type_filter == 'unit':
        entities_qs = entities_qs.filter(unit_profile__isnull=False)
    elif type_filter == 'individual_participant':
        entities_qs = entities_qs.filter(individual_participant_profile__isnull=False)
    elif type_filter == 'organizer':
        entities_qs = entities_qs.filter(organizer_profile__isnull=False)
    else:
        entities_qs = entities_qs.filter(
            Q(unit_profile__isnull=False)
            | Q(individual_participant_profile__isnull=False)
            | Q(organizer_profile__isnull=False)
        )

    # Filter by search query
    if search_query:
        entities_qs = entities_qs.filter(
            Q(scout_unit_name__icontains=search_query)
            | Q(individual_participant_profile__first_name__icontains=search_query)
            | Q(individual_participant_profile__last_name__icontains=search_query)
            | Q(organizer_profile__first_name__icontains=search_query)
            | Q(organizer_profile__last_name__icontains=search_query)
        )

    # Filter by status
    if status_filter == 'paid':
        entities_qs = entities_qs.filter(paid=True)
    elif status_filter == 'unpaid':
        entities_qs = entities_qs.filter(paid=False)
    elif status_filter == 'confirmed':
        entities_qs = entities_qs.filter(confirmed=True)
    elif status_filter == 'unconfirmed':
        entities_qs = entities_qs.filter(confirmed=False)

    entities_qs = entities_qs.order_by('-created_at')
    paginator = Paginator(entities_qs, MANAGE_ENTITIES_PAGE_SIZE)
    page_obj = paginator.get_page(page_number)

    # Prepare current page data with type information.
    entities_data = []
    for entity in page_obj.object_list:
        if hasattr(entity, 'unit_profile'):
            entities_data.append({
                'entity': entity,
                'type': 'unit',
                'type_display': _('Unit'),
                'name': entity.scout_unit_name or _('Unnamed Unit'),
                'unit': entity.unit_profile,
            })
            continue

        if hasattr(entity, 'individual_participant_profile'):
            participant = entity.individual_participant_profile
            entities_data.append({
                'entity': entity,
                'type': 'individual_participant',
                'type_display': _('Individual Participant'),
                'name': f"{participant.first_name} {participant.last_name}",
                'participant': participant,
            })
            continue

        if hasattr(entity, 'organizer_profile'):
            organizer = entity.organizer_profile
            entities_data.append({
                'entity': entity,
                'type': 'organizer',
                'type_display': _('Organizer'),
                'name': f"{organizer.first_name} {organizer.last_name}",
                'organizer': organizer,
            })
    
    context = {
        'entities_data': entities_data,
        'search_query': search_query,
        'type_filter': type_filter,
        'status_filter': status_filter,
        'page_obj': page_obj,
        'manage_entities_page_size': MANAGE_ENTITIES_PAGE_SIZE,
    }
    return render(request, 'SkaRe/manage_entities.html', context)


@login_required
def manage_unit_editors(request, unit_id):
    """View for managing editors of a unit."""
    unit = get_object_or_404(Unit, id=unit_id)
    
    # Only owner can manage editors
    if unit.entity.created_by != request.user:
        messages.error(request, _('Only the owner can manage editors.'))
        return redirect('SkaRe:list_units')

    # Check if unit can be edited
    if not unit.entity.can_be_edited(request.user):
        messages.error(request, _('This unit\'s editors cannot be edited after the editing deadline.'))
        return redirect('SkaRe:list_units')
    
    if request.method == 'POST':
        action = request.POST.get('action')
        username = request.POST.get('username', '').strip()
        
        if action == 'add' and username:
            try:
                user_to_add = User.objects.get(username=username)
                if user_to_add == request.user:
                    messages.warning(request, _('You cannot add yourself as an editor.'))
                elif unit.entity.editors.filter(id=user_to_add.id).exists():
                    messages.warning(request, _('User "{username}" is already an editor.').format(username=username))
                else:
                    unit.entity.editors.add(user_to_add)
                    messages.success(request, _('User "{username}" added as editor.').format(username=username))
            except User.DoesNotExist:
                messages.error(request, _('User "{username}" not found.').format(username=username))
        
        elif action == 'remove':
            user_id = request.POST.get('user_id')
            if user_id:
                try:
                    user_to_remove = User.objects.get(id=user_id)
                    unit.entity.editors.remove(user_to_remove)
                    messages.success(request, _('User "{username}" removed from editors.').format(username=user_to_remove.username))
                except User.DoesNotExist:
                    messages.error(request, _('User not found.'))
        
        return redirect('SkaRe:manage_unit_editors', unit_id=unit_id)
    
    context = {
        'unit': unit,
        'editors': unit.entity.editors.all(),
    }
    return render(request, 'SkaRe/manage_editors.html', context)


@login_required
def manage_individual_participant_editors(request, participant_id):
    """View for managing editors of an individual participant."""
    participant = get_object_or_404(IndividualParticipant, id=participant_id)
    
    # Only owner can manage editors
    if participant.entity.created_by != request.user:
        messages.error(request, _('Only the owner can manage editors.'))
        return redirect('SkaRe:list_individual_participants')

    # Check if participant can be edited
    if not participant.entity.can_be_edited(request.user):
        messages.error(request, _('This participant\'s editors cannot be edited after the editing deadline.'))
        return redirect('SkaRe:list_individual_participants')
    
    if request.method == 'POST':
        action = request.POST.get('action')
        username = request.POST.get('username', '').strip()
        
        if action == 'add' and username:
            try:
                user_to_add = User.objects.get(username=username)
                if user_to_add == request.user:
                    messages.warning(request, _('You cannot add yourself as an editor.'))
                elif participant.entity.editors.filter(id=user_to_add.id).exists():
                    messages.warning(request, _('User "{username}" is already an editor.').format(username=username))
                else:
                    participant.entity.editors.add(user_to_add)
                    messages.success(request, _('User "{username}" added as editor.').format(username=username))
            except User.DoesNotExist:
                messages.error(request, _('User "{username}" not found.').format(username=username))
        
        elif action == 'remove':
            user_id = request.POST.get('user_id')
            if user_id:
                try:
                    user_to_remove = User.objects.get(id=user_id)
                    participant.entity.editors.remove(user_to_remove)
                    messages.success(request, _('User "{username}" removed from editors.').format(username=user_to_remove.username))
                except User.DoesNotExist:
                    messages.error(request, _('User not found.'))
        
        return redirect('SkaRe:manage_individual_participant_editors', participant_id=participant_id)
    
    context = {
        'participant': participant,
        'editors': participant.entity.editors.all(),
        'entity_type': 'individual_participant',
    }
    return render(request, 'SkaRe/manage_editors.html', context)


@login_required
def manage_organizer_editors(request, organizer_id):
    """View for managing editors of an organizer."""
    organizer = get_object_or_404(Organizer, id=organizer_id)
    
    # Only owner can manage editors
    if organizer.entity.created_by != request.user:
        messages.error(request, _('Only the owner can manage editors.'))
        return redirect('SkaRe:list_organizers')
    
    # Check if organizer can be edited
    if not organizer.entity.can_be_edited(request.user):
        messages.error(request, _('This organizer\'s editors cannot be edited after the editing deadline.'))
        return redirect('SkaRe:list_organizers')
    
    if request.method == 'POST':
        action = request.POST.get('action')
        username = request.POST.get('username', '').strip()
        
        if action == 'add' and username:
            try:
                user_to_add = User.objects.get(username=username)
                if user_to_add == request.user:
                    messages.warning(request, _('You cannot add yourself as an editor.'))
                elif organizer.entity.editors.filter(id=user_to_add.id).exists():
                    messages.warning(request, _('User "{username}" is already an editor.').format(username=username))
                else:
                    organizer.entity.editors.add(user_to_add)
                    messages.success(request, _('User "{username}" added as editor.').format(username=username))
            except User.DoesNotExist:
                messages.error(request, _('User "{username}" not found.').format(username=username))
        
        elif action == 'remove':
            user_id = request.POST.get('user_id')
            if user_id:
                try:
                    user_to_remove = User.objects.get(id=user_id)
                    organizer.entity.editors.remove(user_to_remove)
                    messages.success(request, _('User "{username}" removed from editors.').format(username=user_to_remove.username))
                except User.DoesNotExist:
                    messages.error(request, _('User not found.'))
        
        return redirect('SkaRe:manage_organizer_editors', organizer_id=organizer_id)
    
    context = {
        'organizer': organizer,
        'editors': organizer.entity.editors.all(),
        'entity_type': 'organizer',
    }
    return render(request, 'SkaRe/manage_editors.html', context)


_SAIL_REGISTRY_CACHE_KEY = "sail_registry_rows"


def _fetch_sheet_csv(url):
    """Fetch the published Google Sheets CSV and return raw text.

    Decodes as UTF-8-sig to strip any BOM. Raises on network errors.
    """
    req = urllib.request.Request(url)
    with urllib.request.urlopen(req, timeout=10) as response:
        return response.read().decode('utf-8-sig')


def _get_registry_rows():
    """Return parsed registry rows from cache, fetching if needed."""
    rows = cache.get(_SAIL_REGISTRY_CACHE_KEY)
    if rows is None:
        raw = _fetch_sheet_csv(settings.SAIL_REGISTRY_SHEET_URL)
        lines = io.StringIO(raw).readlines()
        # Row 1 is the sheet title, row 2 is metadata — actual headers are on row 3
        reader = csv.DictReader(lines[2:])
        rows = [row for row in reader if any(v.strip() for v in row.values())]
        cache.set(_SAIL_REGISTRY_CACHE_KEY, rows, settings.SAIL_REGISTRY_CACHE_TTL)
    return rows


@login_required
def boat_sail_lookup(request):
    """AJAX: look up a sail number in the Google Sheets registry."""
    q = request.GET.get('q', '').strip()
    if not q:
        return JsonResponse({'error': 'missing q'}, status=400)

    try:
        rows = _get_registry_rows()
    except Exception:
        return JsonResponse({'error': 'registry unavailable'}, status=503)

    match = None
    q_lower = q.lower()
    for row in rows:
        sail_num = row.get('plach. číslo', '').strip()
        if sail_num.lower() == q_lower:
            match = row
            break
        # Numeric normalisation: "14" matches "014", etc.
        try:
            if int(sail_num) == int(q):
                match = row
                break
        except (ValueError, TypeError):
            pass

    if match is None:
        return JsonResponse({'error': 'not found'}, status=404)

    # Parse compound 'typ' field: "šalupa - P550 - Černá Eskadra"
    typ = match.get('typ', '').strip()
    typ_parts = [p.strip() for p in typ.split(' - ')] if typ else []
    subtype = typ_parts[0] if len(typ_parts) > 0 else ''
    class_name = typ_parts[1] if len(typ_parts) > 1 else ''

    # Sail area: Czech decimal comma → dot
    # Column header starts with 'plocha' (full name may include ', datum měření' suffix)
    sail_area_raw = ''
    for key, val in match.items():
        if key.lower().startswith('plocha'):
            sail_area_raw = val.strip()
            break
    sail_area = sail_area_raw.replace(',', '.') if sail_area_raw else ''

    return JsonResponse({
        'sail_number': match.get('plach. číslo', '').strip(),
        'boat_name': match.get('Jméno', '').strip(),
        'class_name': class_name,
        'subtype': subtype,
        'sail_area': sail_area,
        'harbor_number': match.get('ev. č.', '').strip(),
        'harbor_name': match.get('přístav', '').strip(),
        'contact_person': match.get('oddíl', '').strip(),
    })


@login_required
def boat_my_unit(request):
    """AJAX: return the most recently created Unit for the current user."""
    unit = (
        Unit.objects
        .filter(entity__created_by=request.user)
        .select_related('entity')
        .order_by('-entity__created_at')
        .first()
    )
    if not unit:
        return JsonResponse({}, status=404)
    return JsonResponse({
        'harbor_number': unit.entity.scout_unit_evidence_id,
        'harbor_name': unit.entity.scout_unit_name,
        'contact_person': unit.contact_person_name,
    })


@login_required
def boat_list(request):
    boats = Boat.objects.select_related('boat_class', 'created_by').order_by('name')
    return render(request, 'SkaRe/boats/list.html', {'boats': boats})


@login_required
def boat_detail(request, boat_id):
    boat = get_object_or_404(Boat.objects.select_related('boat_class', 'created_by'), id=boat_id)
    return render(request, 'SkaRe/boats/detail.html', {
        'boat': boat,
        'can_edit': boat.can_be_edited(request.user),
        'is_creator': boat.created_by == request.user,
    })


@login_required
def boat_register(request):
    has_unit = Unit.objects.filter(entity__created_by=request.user).exists()
    if request.method == 'POST':
        form = BoatForm(request.POST)
        if form.is_valid():
            boat = form.save(commit=False)
            boat.created_by = request.user
            boat.save()
            messages.success(request, _('Boat registered successfully.'))
            return redirect('SkaRe:boat_detail', boat_id=boat.pk)
    else:
        form = BoatForm()
    return render(request, 'SkaRe/boats/form.html', {
        'form': form,
        'has_unit': has_unit,
        'action': 'register',
    })


@login_required
def boat_edit(request, boat_id):
    boat = get_object_or_404(Boat.objects.select_related('boat_class', 'created_by'), id=boat_id)
    if not boat.can_be_edited(request.user):
        messages.error(request, _('You do not have permission to edit this boat.'))
        return redirect('SkaRe:boat_detail', boat_id=boat_id)
    has_unit = Unit.objects.filter(entity__created_by=request.user).exists()
    if request.method == 'POST':
        form = BoatForm(request.POST, instance=boat)
        if form.is_valid():
            form.save()
            messages.success(request, _('Boat updated successfully.'))
            return redirect('SkaRe:boat_detail', boat_id=boat.pk)
    else:
        form = BoatForm(instance=boat)
    return render(request, 'SkaRe/boats/form.html', {
        'form': form,
        'boat': boat,
        'has_unit': has_unit,
        'action': 'edit',
    })


@login_required
def boat_delete(request, boat_id):
    boat = get_object_or_404(Boat, id=boat_id)
    if boat.created_by != request.user:
        messages.error(request, _('Only the boat creator can delete it.'))
        return redirect('SkaRe:boat_detail', boat_id=boat_id)
    if request.method == 'POST':
        boat.delete()
        messages.success(request, _('Boat deleted successfully.'))
        return redirect('SkaRe:boat_list')
    return render(request, 'SkaRe/boats/confirm_delete.html', {'boat': boat})


@login_required
def boat_lend(request, boat_id):
    """Manage which users can see and use this boat in crew registration."""
    boat = get_object_or_404(Boat, id=boat_id)

    if not boat.can_be_edited(request.user):
        messages.error(request, _('You do not have permission to manage lending for this boat.'))
        return redirect('SkaRe:boat_detail', boat_id=boat_id)

    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'add':
            username = request.POST.get('username', '').strip()
            try:
                user_to_add = User.objects.get(username=username)
                if user_to_add == request.user:
                    messages.warning(request, _('You cannot lend to yourself.'))
                elif boat.visible_to.filter(id=user_to_add.id).exists():
                    messages.warning(request, _('User "{username}" already has access.').format(username=username))
                else:
                    boat.visible_to.add(user_to_add)
                    messages.success(request, _('User "{username}" can now see this boat.').format(username=username))
            except User.DoesNotExist:
                messages.error(request, _('User "{username}" not found.').format(username=username))
        elif action == 'remove':
            user_id = request.POST.get('user_id')
            try:
                user_to_remove = User.objects.get(id=user_id)
                boat.visible_to.remove(user_to_remove)
                messages.success(request, _('Access removed for user "{username}".').format(username=user_to_remove.username))
            except (User.DoesNotExist, ValueError):
                pass
        return redirect('SkaRe:boat_lend', boat_id=boat_id)

    return render(request, 'SkaRe/boats/lend.html', {
        'boat': boat,
        'lent_to': boat.visible_to.all(),
    })


@login_required
def person_lend(request, person_id):
    """Manage which users can see and use this person in crew registration."""
    person = get_object_or_404(Person, id=person_id)

    # Determine if request.user can manage lending for this person
    can_manage = False
    if hasattr(person, 'regularparticipant'):
        entity = person.regularparticipant.unit.entity
        can_manage = entity.created_by == request.user or entity.editors.filter(id=request.user.id).exists()
    elif hasattr(person, 'individualparticipant'):
        entity = person.individualparticipant.entity
        can_manage = entity.created_by == request.user or entity.editors.filter(id=request.user.id).exists()
    elif hasattr(person, 'organizer'):
        entity = person.organizer.entity
        can_manage = entity.created_by == request.user or entity.editors.filter(id=request.user.id).exists()

    if not can_manage:
        messages.error(request, _('You do not have permission to manage lending for this person.'))
        return redirect('SkaRe:home')

    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'add':
            username = request.POST.get('username', '').strip()
            try:
                user_to_add = User.objects.get(username=username)
                if person.visible_to.filter(id=user_to_add.id).exists():
                    messages.warning(request, _('User "{username}" already has access.').format(username=username))
                else:
                    person.visible_to.add(user_to_add)
                    messages.success(request, _('User "{username}" can now see this person.').format(username=username))
            except User.DoesNotExist:
                messages.error(request, _('User "{username}" not found.').format(username=username))
        elif action == 'remove':
            user_id = request.POST.get('user_id')
            try:
                user_to_remove = User.objects.get(id=user_id)
                person.visible_to.remove(user_to_remove)
                messages.success(request, _('Access removed for user "{username}".').format(username=user_to_remove.username))
            except (User.DoesNotExist, ValueError):
                pass
        return redirect('SkaRe:person_lend', person_id=person_id)

    return render(request, 'SkaRe/persons/lend.html', {
        'person': person,
        'lent_to': person.visible_to.all(),
    })


@login_required
def crew_register(request):
    """Register a new crew."""
    is_infodesk = request.user.groups.filter(name='InfoDesk').exists()
    if not EventSettings.is_crew_registration_open() and not is_infodesk:
        messages.error(request, _('Crew registration is closed.'))
        return redirect('SkaRe:home')

    form = CrewRegistrationForm(user=request.user, data=request.POST or None)
    if request.method == 'POST' and form.is_valid():
        boat = form.cleaned_data['boat']
        category = form.cleaned_data['category']
        if Crew.objects.filter(boat=boat, category=category).exists():
            form.add_error(None, _('A crew for this boat and category already exists.'))
        else:
            try:
                with transaction.atomic():
                    crew = Crew.objects.create(
                        boat=boat, category=category, created_by=request.user
                    )
                    CrewMember.objects.create(
                        crew=crew,
                        role=CrewMember.ROLE_HELMSMAN,
                        participant=form.cleaned_data['helmsman'],
                    )
                    for i in range(1, 5):
                        person = form.cleaned_data.get(f'crew_member_{i}')
                        if person:
                            CrewMember.objects.create(
                                crew=crew, role=CrewMember.ROLE_CREW, participant=person
                            )
            except IntegrityError:
                form.add_error(None, _('A crew for this boat and category already exists.'))
            else:
                messages.success(request, _('Crew registered successfully.'))
                return redirect('SkaRe:crew_detail', crew_id=crew.id)

    crew_fields = [
        ('helmsman', _('Helmsman')),
        ('crew_member_1', _('Crew member 1')),
        ('crew_member_2', _('Crew member 2')),
        ('crew_member_3', _('Crew member 3')),
        ('crew_member_4', _('Crew member 4')),
    ]
    return render(request, 'SkaRe/crews/register.html', {'form': form, 'crew_fields': crew_fields})


@login_required
def crew_list(request):
    """List crews created by the current user."""
    crews = Crew.objects.filter(created_by=request.user).select_related('boat', 'boat__boat_class').prefetch_related('members')
    return render(request, 'SkaRe/crews/list.html', {'crews': crews})


@login_required
def crew_detail(request, crew_id):
    """View crew details."""
    crew = get_object_or_404(Crew, id=crew_id)
    if not crew.can_be_edited(request.user):
        messages.error(request, _('You do not have permission to view this crew.'))
        return redirect('SkaRe:crew_list')
    members = crew.members.select_related('participant').order_by('-role')
    can_edit = crew.can_be_edited(request.user)
    return render(request, 'SkaRe/crews/detail.html', {'crew': crew, 'members': members, 'can_edit': can_edit})


@login_required
def crew_edit(request, crew_id):
    """Edit an existing crew."""
    crew = get_object_or_404(Crew, id=crew_id)
    if not crew.can_be_edited(request.user):
        messages.error(request, _('You do not have permission to edit this crew.'))
        return redirect('SkaRe:crew_list')

    is_infodesk = request.user.groups.filter(name='InfoDesk').exists()
    if not EventSettings.is_crew_registration_open() and not is_infodesk:
        messages.error(request, _('Crew registration is closed.'))
        return redirect('SkaRe:crew_detail', crew_id=crew_id)

    helmsman_member = crew.members.filter(role=CrewMember.ROLE_HELMSMAN).first()
    crew_members = list(crew.members.filter(role=CrewMember.ROLE_CREW).values_list('participant_id', flat=True))

    initial = {
        'boat': crew.boat_id,
        'category': crew.category,
        'helmsman': helmsman_member.participant_id if helmsman_member else None,
    }
    for i, pid in enumerate(crew_members[:4], start=1):
        initial[f'crew_member_{i}'] = pid

    form = CrewRegistrationForm(user=request.user, data=request.POST or None, initial=initial)
    if request.method == 'POST' and form.is_valid():
        boat = form.cleaned_data['boat']
        category = form.cleaned_data['category']
        if Crew.objects.filter(boat=boat, category=category).exclude(pk=crew_id).exists():
            form.add_error(None, _('A crew for this boat and category already exists.'))
        else:
            try:
                with transaction.atomic():
                    crew.boat = boat
                    crew.category = category
                    crew.save()
                    crew.members.all().delete()
                    CrewMember.objects.create(
                        crew=crew, role=CrewMember.ROLE_HELMSMAN,
                        participant=form.cleaned_data['helmsman'],
                    )
                    for i in range(1, 5):
                        person = form.cleaned_data.get(f'crew_member_{i}')
                        if person:
                            CrewMember.objects.create(crew=crew, role=CrewMember.ROLE_CREW, participant=person)
            except IntegrityError:
                form.add_error(None, _('A crew for this boat and category already exists.'))
            else:
                messages.success(request, _('Crew updated successfully.'))
                return redirect('SkaRe:crew_detail', crew_id=crew.id)

    crew_fields = [
        ('helmsman', _('Helmsman')),
        ('crew_member_1', _('Crew member 1')),
        ('crew_member_2', _('Crew member 2')),
        ('crew_member_3', _('Crew member 3')),
        ('crew_member_4', _('Crew member 4')),
    ]
    return render(request, 'SkaRe/crews/edit.html', {'form': form, 'crew': crew, 'crew_fields': crew_fields})


@login_required
def crew_delete(request, crew_id):
    """Delete a crew."""
    crew = get_object_or_404(Crew, id=crew_id)
    if not crew.can_be_edited(request.user):
        messages.error(request, _('You do not have permission to delete this crew.'))
        return redirect('SkaRe:crew_list')

    if request.method == 'POST':
        crew.delete()
        messages.success(request, _('Crew deleted.'))
        return redirect('SkaRe:crew_list')

    return render(request, 'SkaRe/crews/confirm_delete.html', {'crew': crew})


@login_required
def crew_export_csv(request):
    """Staff-only CSV export of all crews and their members."""
    if not request.user.is_staff:
        messages.error(request, _('Staff access required.'))
        return redirect('SkaRe:home')

    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="crews.csv"'
    # BOM for Excel UTF-8 compatibility
    response.write('\ufeff')

    writer = csv.writer(response)
    writer.writerow([
        'crew_id', 'category', 'boat_sail_number', 'boat_name',
        'boat_class', 'sail_area', 'role',
        'first_name', 'last_name', 'date_of_birth', 'scout_category',
        'participant_type', 'unit_name',
    ])

    members = (
        CrewMember.objects
        .select_related('crew', 'crew__boat', 'crew__boat__boat_class', 'participant')
        .order_by('crew__id', '-role')
    )

    for m in members:
        crew = m.crew
        person = m.participant
        participant_type = ''
        unit_name = ''
        if hasattr(person, 'regularparticipant'):
            participant_type = 'RegularParticipant'
            unit_name = person.regularparticipant.unit.entity.scout_unit_name
        elif hasattr(person, 'individualparticipant'):
            participant_type = 'IndividualParticipant'
        elif hasattr(person, 'organizer'):
            participant_type = 'Organizer'

        writer.writerow([
            crew.id,
            crew.category,
            crew.boat.sail_number,
            crew.boat.name,
            crew.boat.boat_class.name if crew.boat.boat_class else '',
            crew.boat.sail_area or '',
            m.role,
            person.first_name,
            person.last_name,
            person.date_of_birth,
            person.category or '',
            participant_type,
            unit_name,
        ])

    return response
