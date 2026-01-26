from django.contrib import admin
from .models import IndividualParticipant, Organizer, ScoutUnit, Unit, RegularParticipant, EventSettings
from solo.admin import SingletonModelAdmin

# This ensures the admin jumps directly to the edit form
admin.site.register(EventSettings, SingletonModelAdmin)
admin.site.register(Unit)
admin.site.register(RegularParticipant)
admin.site.register(IndividualParticipant)
admin.site.register(Organizer)
admin.site.register(ScoutUnit)