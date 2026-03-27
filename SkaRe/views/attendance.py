from django.http import HttpResponse
from ..permissions import infodesk_required


@infodesk_required
def attendance_units_list(request):
    return HttpResponse('TODO: Plan B', status=200)


@infodesk_required
def attendance_unit_detail(request, unit_id):
    return HttpResponse('TODO: Plan B', status=200)


@infodesk_required
def attendance_individuals_list(request):
    return HttpResponse('TODO: Plan B', status=200)


@infodesk_required
def attendance_organizers_list(request):
    return HttpResponse('TODO: Plan B', status=200)


@infodesk_required
def attendance_set_status(request, person_id):
    return HttpResponse('TODO: Plan B', status=200)


@infodesk_required
def attendance_unit_mark_all_arrived(request, unit_id):
    return HttpResponse('TODO: Plan B', status=200)
