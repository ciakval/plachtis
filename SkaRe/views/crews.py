import csv

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib import messages
from django.http import HttpResponse
from django.utils.translation import gettext as _
from django.db import IntegrityError, transaction
from django.db.models import Count, Q
from ..models import Boat, Person, Crew, CrewMember, EventSettings
from ..forms import CrewRegistrationForm
from .exports import _csv_safe, _fmt_dt, _age


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


_CREW_CSV_HEADER = [
    'registration_number', 'category', 'category',
    'sail_number', 'ne', 'harbor_number', 'harbor_name',
    'helmsman', 'crew1', 'crew2', 'crew3', 'crew4',
    'helmsman_age', 'crew1_age', 'crew2_age', 'crew3_age', 'crew4_age',
    'owner', 'registered_at', 'boat_id', 'sail_number',
    'boat_name', 'boat_class', 'sail_area',
]


def _crew_csv_row(crew):
    helmsman = None
    crew_members = []
    for m in sorted(crew.members.all(), key=lambda x: x.id):
        if m.role == CrewMember.ROLE_HELMSMAN:
            helmsman = m
        else:
            crew_members.append(m)

    slots = (crew_members + [None] * 4)[:4]

    def name(m):
        return _csv_safe(str(m.participant)) if m else ''

    def member_age(m):
        if m and m.participant.date_of_birth:
            return _age(m.participant.date_of_birth)
        return ''

    contact = crew.boat.contact_person or ''
    phone = crew.boat.contact_phone or ''
    if contact and phone:
        owner_info = f"{contact} / {phone}"
    else:
        owner_info = contact or phone

    return [
        crew.id,
        crew.category,
        crew.category,
        _csv_safe(crew.boat.sail_number),
        'NE',
        _csv_safe(crew.boat.harbor_number),
        _csv_safe(crew.boat.harbor_name),
        name(helmsman),
        name(slots[0]),
        name(slots[1]),
        name(slots[2]),
        name(slots[3]),
        member_age(helmsman),
        member_age(slots[0]),
        member_age(slots[1]),
        member_age(slots[2]),
        member_age(slots[3]),
        _csv_safe(owner_info),
        _fmt_dt(crew.created_at),
        crew.boat.id,
        _csv_safe(crew.boat.sail_number),
        _csv_safe(crew.boat.name),
        crew.boat.boat_class.name if crew.boat.boat_class else '',
        str(crew.boat.sail_area or '').replace('.',','),
    ]


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

    writer = csv.writer(response, delimiter=';')
    writer.writerow(_CREW_CSV_HEADER)

    crews = (
        Crew.objects
        .select_related('boat', 'boat__boat_class')
        .prefetch_related('members__participant')
        .order_by('id')
    )
    for crew in crews:
        writer.writerow(_crew_csv_row(crew))

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


@login_required
def crew_all(request):
    if not request.user.is_staff:
        messages.error(request, _('Staff access required.'))
        return redirect('SkaRe:home')

    q = request.GET.get('q', '').strip()
    category = request.GET.get('category', '').strip()

    qs = Crew.objects.select_related(
        'boat', 'boat__boat_class'
    ).prefetch_related('members__participant')

    if category:
        qs = qs.filter(category=category)
    if q:
        qs = qs.filter(
            Q(boat__name__icontains=q) |
            Q(members__participant__first_name__icontains=q) |
            Q(members__participant__last_name__icontains=q)
        ).distinct()

    total_crews = Crew.objects.count()
    category_counts = {
        row['category']: row['count']
        for row in Crew.objects.values('category').annotate(count=Count('id'))
    }
    category_stats_list = [
        (code, label, category_counts.get(code, 0))
        for code, label in Crew.CATEGORY_CHOICES
    ]

    crew_rows = []
    for crew in qs:
        members_list = list(crew.members.all())
        helmsman = next(
            (m.participant for m in members_list if m.role == CrewMember.ROLE_HELMSMAN),
            None,
        )
        crew_rows.append({
            'crew': crew,
            'helmsman': helmsman,
            'member_count': len(members_list),
        })

    return render(request, 'SkaRe/crews/all.html', {
        'crew_rows': crew_rows,
        'total_crews': total_crews,
        'filtered_count': len(crew_rows),
        'category_stats_list': category_stats_list,
        'category_choices': Crew.CATEGORY_CHOICES,
        'q': q,
        'selected_category': category,
    })


@login_required
def crew_all_export_csv(request):
    if not request.user.is_staff:
        messages.error(request, _('Staff access required.'))
        return redirect('SkaRe:home')

    q = request.GET.get('q', '').strip()
    category = request.GET.get('category', '').strip()

    qs = Crew.objects.select_related('boat', 'boat__boat_class')
    if category:
        qs = qs.filter(category=category)
    if q:
        qs = qs.filter(
            Q(boat__name__icontains=q) |
            Q(members__participant__first_name__icontains=q) |
            Q(members__participant__last_name__icontains=q)
        ).distinct()

    if category:
        filename = f'crews_{category}.csv'
    elif q:
        filename = 'crews_search.csv'
    else:
        filename = 'crews.csv'

    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    response.write('\ufeff')

    writer = csv.writer(response, delimiter=';')
    writer.writerow(_CREW_CSV_HEADER)

    crews = (
        qs
        .select_related('boat', 'boat__boat_class')
        .prefetch_related('members__participant')
        .order_by('id')
    )
    for crew in crews:
        writer.writerow(_crew_csv_row(crew))

    return response


@login_required
def crew_detail_staff(request, crew_id):
    if not request.user.is_staff:
        messages.error(request, _('Staff access required.'))
        return redirect('SkaRe:home')
    crew = get_object_or_404(Crew, id=crew_id)
    members = crew.members.select_related('participant').order_by('-role')
    return render(request, 'SkaRe/crews/detail_staff.html', {
        'crew': crew,
        'members': members,
    })


@login_required
def crew_export_single_csv(request, crew_id):
    if not request.user.is_staff:
        messages.error(request, _('Staff access required.'))
        return redirect('SkaRe:home')
    crew = get_object_or_404(
        Crew.objects.select_related('boat', 'boat__boat_class').prefetch_related('members__participant'),
        id=crew_id,
    )

    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="crew_{crew_id}.csv"'
    response.write('\ufeff')

    writer = csv.writer(response, delimiter=';')
    writer.writerow(_CREW_CSV_HEADER)
    writer.writerow(_crew_csv_row(crew))

    return response
