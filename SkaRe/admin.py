from django.contrib import admin

from solo.admin import SingletonModelAdmin

from .models import (
    Entity, IndividualParticipant, Organizer, Unit, RegularParticipant,
    EventSettings, BoatClass, Boat,
)

# Existing registrations (unchanged)
admin.site.register(EventSettings, SingletonModelAdmin)
admin.site.register(Unit)
admin.site.register(RegularParticipant)
admin.site.register(IndividualParticipant)
admin.site.register(Organizer)
admin.site.register(Entity)


@admin.register(BoatClass)
class BoatClassAdmin(admin.ModelAdmin):
    list_display = ['name', 'category', 'is_other', 'order']
    list_editable = ['order']
    ordering = ['order', 'name']


@admin.register(Boat)
class BoatAdmin(admin.ModelAdmin):
    list_display = ['__str__', 'boat_class', 'hull_color', 'sail_color',
                    'contact_person', 'created_by', 'created_at']
    list_filter = ['boat_class', 'hull_color']
    search_fields = ['name', 'sail_number']
    raw_id_fields = ['created_by']
