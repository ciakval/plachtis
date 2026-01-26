from django.shortcuts import render, redirect
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.forms import AuthenticationForm
from django.contrib import messages
from .forms import UserRegistrationForm


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
