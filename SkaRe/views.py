from django.shortcuts import render, redirect
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db import transaction
from .forms import UserRegistrationForm, UnitRegistrationForm, RegularParticipantFormSet, ScoutUnitForm
from .models import ScoutUnit, Entity, Unit, RegularParticipant, EventSettings


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
                    # Handle Scout Unit
                    existing_scout_unit = unit_form.cleaned_data.get('existing_scout_unit')
                    if existing_scout_unit:
                        scout_unit = existing_scout_unit
                    else:
                        # Create new scout unit
                        scout_unit = ScoutUnit.objects.create(
                            name=unit_form.cleaned_data['new_scout_unit_name'],
                            evidence_id=unit_form.cleaned_data['new_scout_unit_evidence_id']
                        )
                    
                    # Create Entity
                    entity = Entity.objects.create(
                        created_by=request.user,
                        scout_unit=scout_unit,
                        contact_email=unit_form.cleaned_data['contact_email'],
                        contact_phone=unit_form.cleaned_data['contact_phone'],
                        expected_arrival=unit_form.cleaned_data.get('expected_arrival'),
                        expected_departure=unit_form.cleaned_data.get('expected_departure'),
                        home_town=unit_form.cleaned_data.get('home_town', '')
                    )
                    
                    # Create Unit
                    unit = unit_form.save(commit=False)
                    unit.entity = entity
                    unit.scout_unit = scout_unit
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
                        f'Unit "{scout_unit.name}" registered successfully with {participant_count} participant(s)!'
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
