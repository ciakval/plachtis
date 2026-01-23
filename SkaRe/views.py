from django.shortcuts import render, redirect
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .forms import UserRegistrationForm, GroupForm, ParticipantFormSet
from .models import Group, Participant


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
def group_list(request):
    """
    View to list all groups.
    """
    groups = Group.objects.all().order_by('-created_at')
    return render(request, 'SkaRe/group_list.html', {'groups': groups})


@login_required
def create_group_with_participants(request):
    """
    View to create a group with multiple participants.
    """
    if request.method == 'POST':
        group_form = GroupForm(request.POST)
        
        if group_form.is_valid():
            group = group_form.save()
            participant_formset = ParticipantFormSet(request.POST, instance=group)
            
            if participant_formset.is_valid():
                participant_formset.save()
                messages.success(request, f'Group "{group.name}" created successfully with participants!')
                return redirect('SkaRe:group_list')
            else:
                # If participants are invalid, delete the group and show errors
                group.delete()
                messages.error(request, 'Please correct the errors in the participant forms.')
        else:
            participant_formset = ParticipantFormSet(request.POST)
    else:
        group_form = GroupForm()
        participant_formset = ParticipantFormSet()
    
    return render(request, 'SkaRe/create_group_with_participants.html', {
        'group_form': group_form,
        'participant_formset': participant_formset,
    })


@login_required
def participant_list(request):
    """
    View to list all participants.
    """
    participants = Participant.objects.all().select_related('group').order_by('-created_at')
    return render(request, 'SkaRe/participant_list.html', {'participants': participants})
