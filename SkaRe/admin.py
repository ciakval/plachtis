from django.contrib import admin
from .models import Unit, Participant


@admin.register(Unit)
class UnitAdmin(admin.ModelAdmin):
    list_display = ['unit_name', 'unit_evidence_id', 'contact_person_name', 'contact_email', 'created_at']
    list_filter = ['created_at', 'updated_at']
    search_fields = ['unit_name', 'unit_evidence_id', 'contact_person_name', 'contact_email']
    readonly_fields = ['created_at', 'updated_at']
    fieldsets = (
        ('Unit Information', {
            'fields': ('unit_name', 'unit_evidence_id', 'relevant_information')
        }),
        ('Contact Information', {
            'fields': ('contact_person_name', 'contact_email', 'contact_phone', 'backup_contact_phone')
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(Participant)
class ParticipantAdmin(admin.ModelAdmin):
    list_display = ['first_name', 'last_name', 'nickname', 'category', 'date_of_birth', 'unit', 'created_at']
    list_filter = ['category', 'unit', 'created_at', 'updated_at']
    search_fields = ['first_name', 'last_name', 'nickname']
    readonly_fields = ['created_at', 'updated_at']
    autocomplete_fields = ['unit']
    fieldsets = (
        ('Personal Information', {
            'fields': ('first_name', 'last_name', 'nickname', 'date_of_birth', 'category')
        }),
        ('Health & Dietary', {
            'fields': ('health_restrictions', 'dietary_restrictions', 'relevant_information'),
            'classes': ('collapse',)
        }),
        ('Unit Assignment', {
            'fields': ('unit',)
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
