import csv
import io

from django.contrib import admin, messages
from django.db import transaction
from django.shortcuts import redirect, render
from django.urls import path, reverse
from django.utils.translation import gettext_lazy as _

from solo.admin import SingletonModelAdmin

from .models import (
    Entity, IndividualParticipant, Organizer, Unit, RegularParticipant,
    EventSettings, BoatClass, SailRegistryEntry, Boat,
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


@admin.register(SailRegistryEntry)
class SailRegistryEntryAdmin(admin.ModelAdmin):
    list_display = ['sail_number', 'boat_name', 'class_name', 'harbor_name']
    search_fields = ['sail_number', 'boat_name']

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path(
                'import-csv/',
                self.admin_site.admin_view(self.import_csv_view),
                name='skare_sailregistryentry_import_csv',
            ),
        ]
        return custom_urls + urls

    def import_csv_view(self, request):
        if request.method == 'POST' and request.FILES.get('csv_file'):
            csv_file = request.FILES['csv_file']
            try:
                decoded = csv_file.read().decode('utf-8')
                reader = csv.DictReader(io.StringIO(decoded))
                entries = []
                for row in reader:
                    sail_area = row.get('sail_area', '').strip() or None
                    entries.append(SailRegistryEntry(
                        sail_number=row.get('sail_number', '').strip(),
                        boat_name=row.get('boat_name', '').strip(),
                        class_name=row.get('class_name', '').strip(),
                        subtype=row.get('subtype', '').strip(),
                        sail_area=sail_area,
                        harbor_number=row.get('harbor_number', '').strip(),
                        harbor_name=row.get('harbor_name', '').strip(),
                        contact_person=row.get('contact_person', '').strip(),
                    ))
                with transaction.atomic():
                    SailRegistryEntry.objects.all().delete()
                    SailRegistryEntry.objects.bulk_create(entries)
                self.message_user(
                    request,
                    _('Successfully imported %(count)d entries.') % {'count': len(entries)},
                    messages.SUCCESS,
                )
            except Exception as e:
                self.message_user(
                    request,
                    _('Import failed: %(error)s') % {'error': str(e)},
                    messages.ERROR,
                )
            return redirect(reverse('admin:SkaRe_sailregistryentry_changelist'))

        return render(
            request,
            'admin/SkaRe/sailregistryentry/import_csv.html',
            {'title': _('Import sail registry CSV')},
        )


@admin.register(Boat)
class BoatAdmin(admin.ModelAdmin):
    list_display = ['name', 'sail_number', 'boat_class', 'created_by']
    search_fields = ['name', 'sail_number']
    raw_id_fields = ['created_by']
