from django.contrib import admin
from .models import HelloWorld


# Register your models here.
@admin.register(HelloWorld)
class HelloWorldAdmin(admin.ModelAdmin):
    list_display = ('message', 'created_at')
    readonly_fields = ('created_at',)

