from django.shortcuts import render
from django.http import HttpResponse
from .models import HelloWorld


# Create your views here.
def hello_world(request):
    """Simple hello world view."""
    # Get the first HelloWorld message or create a default one
    hello_messages = HelloWorld.objects.all()
    
    if hello_messages.exists():
        message = hello_messages.first().message
    else:
        message = 'Hello, World!'
    
    return HttpResponse(f'<h1>{message}</h1>')


def hello_world_list(request):
    """View to display all hello world messages."""
    messages = HelloWorld.objects.all().order_by('-created_at')
    return render(request, 'core/hello_world_list.html', {'messages': messages})

