from django.urls import path
from . import views

app_name = 'core'

urlpatterns = [
    path('', views.hello_world, name='hello_world'),
    path('list/', views.hello_world_list, name='hello_world_list'),
]
