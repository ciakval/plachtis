from django.contrib import admin
from .models import Unit, Participant, EventSettings


@admin.register(EventSettings)
class EventSettingsAdmin(admin.ModelAdmin):
    list_display = ['event_name', 'registration_deadline', 'created_at', 'updated_at']
    readonly_fields = ['created_at', 'updated_at']
    fieldsets = (
        ('Event Information', {
            'fields': ('event_name', 'registration_deadline')
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def has_add_permission(self, request):
        # Only allow creating one EventSettings instance
        return not EventSettings.objects.exists()

    def has_delete_permission(self, request, obj=None):
        # Prevent deletion of EventSettings
        return False


@admin.register(Unit)
class UnitAdmin(admin.ModelAdmin):
    list_display = ['unit_name', 'unit_evidence_id', 'contact_person_name', 'contact_email', 'created_by', 'unlocked_for_editing', 'created_at']
    list_filter = ['created_at', 'updated_at', 'created_by', 'unlocked_for_editing', 'is_individual']
    search_fields = ['unit_name', 'unit_evidence_id', 'contact_person_name', 'contact_email']
    readonly_fields = ['created_by', 'created_at', 'updated_at']
    fieldsets = (
        ('Unit Information', {
            'fields': ('unit_name', 'unit_evidence_id', 'is_individual', 'relevant_information')
        }),
        ('Contact Information', {
            'fields': ('contact_person_name', 'contact_email', 'contact_phone', 'backup_contact_phone')
        }),
        ('Security & Permissions', {
            'fields': ('created_by', 'unlocked_for_editing'),
            'description': 'The "unlocked_for_editing" field allows privileged users to unlock units for editing after the registration deadline.'
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        # Staff and superusers can see all units
        if request.user.is_superuser or request.user.is_staff:
            return qs
        # Regular users only see their own units
        return qs.filter(created_by=request.user)


@admin.register(Participant)
class ParticipantAdmin(admin.ModelAdmin):
    list_display = ['first_name', 'last_name', 'nickname', 'category', 'date_of_birth', 'unit', 'created_at']
    list_filter = ['category', 'unit', 'created_at', 'updated_at']
    search_fields = ['first_name', 'last_name', 'nickname', 'unit__unit_name']
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

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        # Staff and superusers can see all participants
        if request.user.is_superuser or request.user.is_staff:
            return qs
        # Regular users only see participants from their own units
        return qs.filter(unit__created_by=request.user)
