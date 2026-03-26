import csv

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib import messages
from django.http import HttpResponse
from django.utils.translation import gettext as _
from django.db import IntegrityError, transaction
from ..models import Boat, Person, Crew, CrewMember, EventSettings
from ..forms import CrewRegistrationForm


@login_required
def crew_register(request):
    """Register a new crew."""
    is_infodesk = request.user.groups.filter(name='InfoDesk').exists()
    if not EventSettings.is_crew_registration_open() and not is_infodesk:
        messages.error(request, _('Crew registration is closed.'))
        return redirect('SkaRe:home')

    form = CrewRegistrationForm(user=request.user, data=request.POST or None)
    if request.method == 'POST' and form.is_valid():
        boat = form.cleaned_data['boat']
        category = form.cleaned_data['category']
        if Crew.objects.filter(boat=boat, category=category).exists():
            form.add_error(None, _('A crew for this boat and category already exists.'))
        else:
            try:
                with transaction.atomic():
                    crew = Crew.objects.create(
                        boat=boat, category=category, created_by=request.user
                    )
                    CrewMember.objects.create(
                        crew=crew,
                        role=CrewMember.ROLE_HELMSMAN,
                        participant=form.cleaned_data['helmsman'],
                    )
                    for i in range(1, 5):
                        person = form.cleaned_data.get(f'crew_member_{i}')
                        if person:
                            CrewMember.objects.create(
                                crew=crew, role=CrewMember.ROLE_CREW, participant=person
                            )
            except IntegrityError:
                form.add_error(None, _('A crew for this boat and category already exists.'))
            else:
                messages.success(request, _('Crew registered successfully.'))
                return redirect('SkaRe:crew_detail', crew_id=crew.id)

    crew_fields = [
        ('helmsman', _('Helmsman')),
        ('crew_member_1', _('Crew member 1')),
        ('crew_member_2', _('Crew member 2')),
        ('crew_member_3', _('Crew member 3')),
        ('crew_member_4', _('Crew member 4')),
    ]
    return render(request, 'SkaRe/crews/register.html', {'form': form, 'crew_fields': crew_fields})


@login_required
def crew_list(request):
    """List crews created by the current user."""
    crews = Crew.objects.filter(created_by=request.user).select_related('boat', 'boat__boat_class').prefetch_related('members')
    return render(request, 'SkaRe/crews/list.html', {'crews': crews})


@login_required
def crew_detail(request, crew_id):
    """View crew details."""
    crew = get_object_or_404(Crew, id=crew_id)
    if not crew.can_be_edited(request.user):
        messages.error(request, _('You do not have permission to view this crew.'))
        return redirect('SkaRe:crew_list')
    members = crew.members.select_related('participant').order_by('-role')
    can_edit = crew.can_be_edited(request.user)
    return render(request, 'SkaRe/crews/detail.html', {'crew': crew, 'members': members, 'can_edit': can_edit})


@login_required
def crew_edit(request, crew_id):
    """Edit an existing crew."""
    crew = get_object_or_404(Crew, id=crew_id)
    if not crew.can_be_edited(request.user):
        messages.error(request, _('You do not have permission to edit this crew.'))
        return redirect('SkaRe:crew_list')

    is_infodesk = request.user.groups.filter(name='InfoDesk').exists()
    if not EventSettings.is_crew_registration_open() and not is_infodesk:
        messages.error(request, _('Crew registration is closed.'))
        return redirect('SkaRe:crew_detail', crew_id=crew_id)

    helmsman_member = crew.members.filter(role=CrewMember.ROLE_HELMSMAN).first()
    crew_members = list(crew.members.filter(role=CrewMember.ROLE_CREW).values_list('participant_id', flat=True))

    initial = {
        'boat': crew.boat_id,
        'category': crew.category,
        'helmsman': helmsman_member.participant_id if helmsman_member else None,
    }
    for i, pid in enumerate(crew_members[:4], start=1):
        initial[f'crew_member_{i}'] = pid

    form = CrewRegistrationForm(user=request.user, data=request.POST or None, initial=initial)
    if request.method == 'POST' and form.is_valid():
        boat = form.cleaned_data['boat']
        category = form.cleaned_data['category']
        if Crew.objects.filter(boat=boat, category=category).exclude(pk=crew_id).exists():
            form.add_error(None, _('A crew for this boat and category already exists.'))
        else:
            try:
                with transaction.atomic():
                    crew.boat = boat
                    crew.category = category
                    crew.save()
                    crew.members.all().delete()
                    CrewMember.objects.create(
                        crew=crew, role=CrewMember.ROLE_HELMSMAN,
                        participant=form.cleaned_data['helmsman'],
                    )
                    for i in range(1, 5):
                        person = form.cleaned_data.get(f'crew_member_{i}')
                        if person:
                            CrewMember.objects.create(crew=crew, role=CrewMember.ROLE_CREW, participant=person)
            except IntegrityError:
                form.add_error(None, _('A crew for this boat and category already exists.'))
            else:
                messages.success(request, _('Crew updated successfully.'))
                return redirect('SkaRe:crew_detail', crew_id=crew.id)

    crew_fields = [
        ('helmsman', _('Helmsman')),
        ('crew_member_1', _('Crew member 1')),
        ('crew_member_2', _('Crew member 2')),
        ('crew_member_3', _('Crew member 3')),
        ('crew_member_4', _('Crew member 4')),
    ]
    return render(request, 'SkaRe/crews/edit.html', {'form': form, 'crew': crew, 'crew_fields': crew_fields})


@login_required
def crew_delete(request, crew_id):
    """Delete a crew."""
    crew = get_object_or_404(Crew, id=crew_id)
    if not crew.can_be_edited(request.user):
        messages.error(request, _('You do not have permission to delete this crew.'))
        return redirect('SkaRe:crew_list')

    if request.method == 'POST':
        crew.delete()
        messages.success(request, _('Crew deleted.'))
        return redirect('SkaRe:crew_list')

    return render(request, 'SkaRe/crews/confirm_delete.html', {'crew': crew})


@login_required
def crew_export_csv(request):
    """Staff-only CSV export of all crews and their members."""
    if not request.user.is_staff:
        messages.error(request, _('Staff access required.'))
        return redirect('SkaRe:home')

    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="crews.csv"'
    # BOM for Excel UTF-8 compatibility
    response.write('\ufeff')

    writer = csv.writer(response)
    writer.writerow([
        'crew_id', 'category', 'boat_sail_number', 'boat_name',
        'boat_class', 'sail_area', 'role',
        'first_name', 'last_name', 'date_of_birth', 'scout_category',
        'participant_type', 'unit_name',
    ])

    members = (
        CrewMember.objects
        .select_related('crew', 'crew__boat', 'crew__boat__boat_class', 'participant')
        .order_by('crew__id', '-role')
    )

    for m in members:
        crew = m.crew
        person = m.participant
        participant_type = ''
        unit_name = ''
        if hasattr(person, 'regularparticipant'):
            participant_type = 'RegularParticipant'
            unit_name = person.regularparticipant.unit.entity.scout_unit_name
        elif hasattr(person, 'individualparticipant'):
            participant_type = 'IndividualParticipant'
        elif hasattr(person, 'organizer'):
            participant_type = 'Organizer'

        writer.writerow([
            crew.id,
            crew.category,
            crew.boat.sail_number,
            crew.boat.name,
            crew.boat.boat_class.name if crew.boat.boat_class else '',
            crew.boat.sail_area or '',
            m.role,
            person.first_name,
            person.last_name,
            person.date_of_birth,
            person.category or '',
            participant_type,
            unit_name,
        ])

    return response


@login_required
def person_lend(request, person_id):
    """Manage which users can see and use this person in crew registration."""
    person = get_object_or_404(Person, id=person_id)

    # Determine if request.user can manage lending for this person
    can_manage = False
    if hasattr(person, 'regularparticipant'):
        entity = person.regularparticipant.unit.entity
        can_manage = entity.created_by == request.user or entity.editors.filter(id=request.user.id).exists()
    elif hasattr(person, 'individualparticipant'):
        entity = person.individualparticipant.entity
        can_manage = entity.created_by == request.user or entity.editors.filter(id=request.user.id).exists()
    elif hasattr(person, 'organizer'):
        entity = person.organizer.entity
        can_manage = entity.created_by == request.user or entity.editors.filter(id=request.user.id).exists()

    if not can_manage:
        messages.error(request, _('You do not have permission to manage lending for this person.'))
        return redirect('SkaRe:home')

    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'add':
            username = request.POST.get('username', '').strip()
            try:
                user_to_add = User.objects.get(username=username)
                if person.visible_to.filter(id=user_to_add.id).exists():
                    messages.warning(request, _('User "{username}" already has access.').format(username=username))
                else:
                    person.visible_to.add(user_to_add)
                    messages.success(request, _('User "{username}" can now see this person.').format(username=username))
            except User.DoesNotExist:
                messages.error(request, _('User "{username}" not found.').format(username=username))
        elif action == 'remove':
            user_id = request.POST.get('user_id')
            try:
                user_to_remove = User.objects.get(id=user_id)
                person.visible_to.remove(user_to_remove)
                messages.success(request, _('Access removed for user "{username}".').format(username=user_to_remove.username))
            except (User.DoesNotExist, ValueError):
                pass
        return redirect('SkaRe:person_lend', person_id=person_id)

    return render(request, 'SkaRe/persons/lend.html', {
        'person': person,
        'lent_to': person.visible_to.all(),
    })
