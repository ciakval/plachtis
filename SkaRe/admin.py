from django.contrib import admin
from .models import Group, Participant


@admin.register(Group)
class GroupAdmin(admin.ModelAdmin):
    list_display = ['name', 'description', 'created_at', 'updated_at']
    list_filter = ['created_at', 'updated_at']
    search_fields = ['name', 'description']
    readonly_fields = ['created_at', 'updated_at']


@admin.register(Participant)
class ParticipantAdmin(admin.ModelAdmin):
    list_display = ['first_name', 'last_name', 'nickname', 'date_of_birth', 'group', 'created_at']
    list_filter = ['group', 'created_at', 'updated_at']
    search_fields = ['first_name', 'last_name', 'nickname']
    readonly_fields = ['created_at', 'updated_at']
    autocomplete_fields = ['group']
    fieldsets = (
        ('Personal Information', {
            'fields': ('first_name', 'last_name', 'nickname', 'date_of_birth')
        }),
        ('Health & Dietary', {
            'fields': ('health_restrictions', 'dietary_restrictions'),
            'classes': ('collapse',)
        }),
        ('Group Assignment', {
            'fields': ('group',)
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
