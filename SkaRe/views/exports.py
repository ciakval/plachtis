from django.http import HttpResponse
from ..permissions import infodesk_required


@infodesk_required
def exports_index(request):
    return HttpResponse('TODO: Plan D', status=200)


@infodesk_required
def exports_kitchen_csv(request):
    return HttpResponse('TODO: Plan D', status=200)


@infodesk_required
def exports_kitchen_print(request):
    return HttpResponse('TODO: Plan D', status=200)


@infodesk_required
def exports_medical_csv(request):
    return HttpResponse('TODO: Plan D', status=200)


@infodesk_required
def exports_medical_print(request):
    return HttpResponse('TODO: Plan D', status=200)
