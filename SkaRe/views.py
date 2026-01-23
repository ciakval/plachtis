from django.shortcuts import render, redirect
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.forms import AuthenticationForm
from django.contrib import messages
from .forms import UserRegistrationForm


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
