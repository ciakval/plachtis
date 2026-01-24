from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .forms import UserRegistrationForm, UnitForm, ParticipantFormSet, IndividualForm
from .models import Unit, Participant


def register(request):
    """
    View for user registration.
    """
    if request.method == 'POST':
        form = UserRegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            username = form.cleaned_data.get('username')
            messages.success(request, f'Account created for {username}! You can now log in.')
            return redirect('SkaRe:login')
    else:
        form = UserRegistrationForm()
    return render(request, 'SkaRe/register.html', {'form': form})


def user_login(request):
    """
    View for user login.
    """
    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            user = authenticate(username=username, password=password)
            if user is not None:
                login(request, user)
                messages.success(request, f'Welcome back, {username}!')
                return redirect('SkaRe:home')
            else:
                messages.error(request, 'Invalid username or password.')
        else:
            messages.error(request, 'Invalid username or password.')
    else:
        form = AuthenticationForm()
    return render(request, 'SkaRe/login.html', {'form': form})


def user_logout(request):
    """
    View for user logout.
    """
    logout(request)
    messages.success(request, 'You have been logged out successfully.')
    return redirect('SkaRe:login')


def home(request):
    """
    Home page view.
    """
    return render(request, 'SkaRe/home.html')


@login_required
def unit_list(request):
    """
    View to list all units.
    """
    units = Unit.objects.all().order_by('-created_at')
    return render(request, 'SkaRe/unit_list.html', {'units': units})


@login_required
def create_unit_with_participants(request):
    """
    View to create a unit with multiple participants.
    """
    if request.method == 'POST':
        unit_form = UnitForm(request.POST)
        
        if unit_form.is_valid():
            unit = unit_form.save()
            participant_formset = ParticipantFormSet(request.POST, instance=unit)
            
            if participant_formset.is_valid():
                participant_formset.save()
                messages.success(request, f'Unit "{unit.unit_name}" created successfully with participants!')
                return redirect('SkaRe:unit_list')
            else:
                # If participants are invalid, delete the unit and show errors
                unit.delete()
                messages.error(request, 'Please correct the errors in the participant forms.')
        else:
            participant_formset = ParticipantFormSet(request.POST)
    else:
        unit_form = UnitForm()
        participant_formset = ParticipantFormSet()
    
    return render(request, 'SkaRe/create_unit_with_participants.html', {
        'unit_form': unit_form,
        'participant_formset': participant_formset,
    })


@login_required
def participant_list(request):
    """
    View to list all participants.
    """
    participants = Participant.objects.all().select_related('unit').order_by('-created_at')
    return render(request, 'SkaRe/participant_list.html', {'participants': participants})


@login_required
def edit_unit_with_participants(request, unit_id):
    """
    View to edit a unit with its participants.
    """
    unit = get_object_or_404(Unit, id=unit_id)
    
    if request.method == 'POST':
        unit_form = UnitForm(request.POST, instance=unit)
        
        if unit_form.is_valid():
            unit = unit_form.save()
            participant_formset = ParticipantFormSet(request.POST, instance=unit)
            
            if participant_formset.is_valid():
                participant_formset.save()
                messages.success(request, f'Unit "{unit.unit_name}" updated successfully!')
                return redirect('SkaRe:unit_list')
            else:
                messages.error(request, 'Please correct the errors in the participant forms.')
        else:
            participant_formset = ParticipantFormSet(request.POST, instance=unit)
    else:
        unit_form = UnitForm(instance=unit)
        participant_formset = ParticipantFormSet(instance=unit)
    
    return render(request, 'SkaRe/edit_unit_with_participants.html', {
        'unit_form': unit_form,
        'participant_formset': participant_formset,
        'unit': unit,
    })


@login_required
def create_individual(request):
    """
    View to create an individual (Unit with one Participant).
    """
    if request.method == 'POST':
        form = IndividualForm(request.POST)
        
        if form.is_valid():
            unit = form.save()
            messages.success(request, f'Individual "{unit.unit_name}" registered successfully!')
            return redirect('SkaRe:unit_list')
        else:
            messages.error(request, 'Please correct the errors in the form.')
    else:
        form = IndividualForm()
    
    return render(request, 'SkaRe/create_individual.html', {
        'form': form,
    })


@login_required
def edit_individual(request, unit_id):
    """
    View to edit an individual (Unit with one Participant).
    """
    unit = get_object_or_404(Unit, id=unit_id, is_individual=True)
    participant = unit.participants.first()
    
    if request.method == 'POST':
        form = IndividualForm(request.POST)
        
        if form.is_valid():
            form.save(unit_instance=unit)
            messages.success(request, f'Individual "{unit.unit_name}" updated successfully!')
            return redirect('SkaRe:unit_list')
        else:
            messages.error(request, 'Please correct the errors in the form.')
    else:
        # Pre-populate form with existing data
        initial_data = {
            'unit_name': unit.unit_name,
            'unit_evidence_id': unit.unit_evidence_id,
            'contact_email': unit.contact_email,
            'contact_phone': unit.contact_phone,
            'backup_contact_phone': unit.backup_contact_phone,
            'expected_arrival': unit.expected_arrival,
            'expected_departure': unit.expected_departure,
            'home_town': unit.home_town,
            'accommodation_expectations': unit.accommodation_expectations,
            'wishes_notes': unit.wishes_notes,
        }
        
        if participant:
            initial_data.update({
                'first_name': participant.first_name,
                'last_name': participant.last_name,
                'nickname': participant.nickname,
                'date_of_birth': participant.date_of_birth,
                'category': participant.category,
                'health_restrictions': participant.health_restrictions,
                'dietary_restrictions': participant.dietary_restrictions,
                'relevant_information': participant.relevant_information,
            })
        
        form = IndividualForm(initial=initial_data)
    
    return render(request, 'SkaRe/edit_individual.html', {
        'form': form,
        'unit': unit,
    })
