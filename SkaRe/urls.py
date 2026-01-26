from django.urls import path
from . import views

app_name = 'SkaRe'

urlpatterns = [
    path('', views.home, name='home'),
    path('user/login/', views.user_login, name='login'),
    path('user/logout/', views.user_logout, name='logout'),
    path('user/register/', views.user_register, name='register'),
    path('unit/register/', views.register_unit, name='register_unit'),
    path('unit/list/', views.list_units, name='list_units'),
    path('unit/edit/<int:unit_id>/', views.edit_unit, name='edit_unit'),
]
