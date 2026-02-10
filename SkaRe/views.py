from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib import messages
from django.db import transaction
from django.db.models import Q
from django import forms
from django.utils.translation import gettext as _
from django.utils.http import url_has_allowed_host_and_scheme
from .forms import (
    UserRegistrationForm, UnitRegistrationForm,
    IndividualParticipantRegistrationForm, OrganizerRegistrationForm,
    validate_czech_phone, get_participant_formset
)
from .form_utils import generate_form_token, is_duplicate_submission, consume_form_token
from .models import (
    Entity, Unit, RegularParticipant, EventSettings,
    IndividualParticipant, Organizer
)


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
        'deadline': EventSettings.get_deadline(),
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
        messages.error(request, _('This unit cannot be edited after the registration deadline.'))
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
        'deadline': EventSettings.get_deadline(),
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
        messages.error(request, _('This participant cannot be edited after the registration deadline.'))
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
        'deadline': EventSettings.get_deadline(),
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
    }
    return render(request, 'SkaRe/list_organizers.html', context)


@login_required
def list_all(request):
    """View for listing all individual participants - staff only."""
    if not request.user.is_staff:
        messages.error(request, _('You do not have permission to view this page.'))
        return redirect('SkaRe:home')
    
    participants = IndividualParticipant.objects.all().select_related('entity')
    organizers = Organizer.objects.all().select_related('entity')
    units = Unit.objects.all().select_related('entity')
    regular_participants = RegularParticipant.objects.all().select_related('unit', 'unit__entity')
    context = {
        'participants': participants,
        'organizers': organizers,
        'units': units,
        'regular_participants': regular_participants,
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
        units = Unit.objects.all().select_related('entity')
        individual_participants = IndividualParticipant.objects.none()
        organizers = Organizer.objects.none()
    elif type_filter == 'individual_participant':
        units = Unit.objects.none()
        individual_participants = IndividualParticipant.objects.all().select_related('entity')
        organizers = Organizer.objects.none()
    elif type_filter == 'organizer':
        units = Unit.objects.none()
        individual_participants = IndividualParticipant.objects.none()
        organizers = Organizer.objects.all().select_related('entity')
    else:
        # Get all units, individual participants, and organizers
        units = Unit.objects.all().select_related('entity')
        individual_participants = IndividualParticipant.objects.all().select_related('entity')
        organizers = Organizer.objects.all().select_related('entity')
    
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
    
    # Calculate totals
    total_scarves = sum(unit.scarf_count for unit in units)
    total_scarves += sum(participant.scarf_count for participant in individual_participants)
    total_scarves += sum(1 for o in organizers if o.wants_scarf)
    
    total_hats = sum(unit.hat_count for unit in units)
    total_hats += sum(participant.hat_count for participant in individual_participants)
    total_hats += sum(1 for o in organizers if o.wants_hat)
    
    context = {
        'units': units,
        'individual_participants': individual_participants,
        'organizers': organizers,
        'search_query': search_query,
        'type_filter': type_filter,
        'total_scarves': total_scarves,
        'total_hats': total_hats,
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
        messages.error(request, _('This organizer cannot be edited after the registration deadline.'))
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
def manage_unit_editors(request, unit_id):
    """View for managing editors of a unit."""
    unit = get_object_or_404(Unit, id=unit_id)
    
    # Only owner can manage editors
    if unit.entity.created_by != request.user:
        messages.error(request, _('Only the owner can manage editors.'))
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
