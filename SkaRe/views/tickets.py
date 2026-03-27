from django.http import HttpResponse
from ..permissions import infodesk_required


@infodesk_required
def ticket_list(request):
    return HttpResponse('TODO: Plan C', status=200)


@infodesk_required
def ticket_detail(request, ticket_id):
    return HttpResponse('TODO: Plan C', status=200)


@infodesk_required
def ticket_set_status(request, ticket_id):
    return HttpResponse('TODO: Plan C', status=200)


@infodesk_required
def ticket_pair_rfid(request, ticket_id):
    return HttpResponse('TODO: Plan C', status=200)


@infodesk_required
def ticket_lookup(request):
    return HttpResponse('TODO: Plan C', status=200)


@infodesk_required
def ticket_create_bulk(request):
    return HttpResponse('TODO: Plan C', status=200)


@infodesk_required
def ticket_on_water(request):
    return HttpResponse('TODO: Plan C', status=200)


@infodesk_required
def ticket_export_csv(request):
    return HttpResponse('TODO: Plan C', status=200)
