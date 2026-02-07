from django.urls import path
from . import views

app_name = 'SkaRe'

urlpatterns = [
    path('', views.home, name='home'),
    path('user/login/', views.user_login, name='login'),
    path('user/logout/', views.user_logout, name='logout'),
    path('user/register/', views.user_register, name='register'),
    path('user/forgot_password/', views.forgot_password, name='forgot_password'),
    path('unit/register/', views.register_unit, name='register_unit'),
    path('unit/list/', views.list_units, name='list_units'),
    path('unit/edit/<int:unit_id>/', views.edit_unit, name='edit_unit'),
    path('unit/editors/<int:unit_id>/', views.manage_unit_editors, name='manage_unit_editors'),
    path('individual/register/', views.register_individual_participant, name='register_individual_participant'),
    path('individual/list/', views.list_individual_participants, name='list_individual_participants'),
    path('individual/edit/<int:participant_id>/', views.edit_individual_participant, name='edit_individual_participant'),
    path('individual/editors/<int:participant_id>/', views.manage_individual_participant_editors, name='manage_individual_participant_editors'),
    path('organizer/register/', views.register_organizer, name='register_organizer'),
    path('organizer/list/', views.list_organizers, name='list_organizers'),
    path('organizer/edit/<int:organizer_id>/', views.edit_organizer, name='edit_organizer'),
    path('organizer/editors/<int:organizer_id>/', views.manage_organizer_editors, name='manage_organizer_editors'),
    path('all/list/', views.list_all, name='list_all'),
]

