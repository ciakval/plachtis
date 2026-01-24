from django.urls import path
from . import views

app_name = 'SkaRe'

urlpatterns = [
    path('', views.home, name='home'),
    path('register/', views.register, name='register'),
    path('login/', views.user_login, name='login'),
    path('logout/', views.user_logout, name='logout'),
    
    # Unit and Participant management
    path('units/', views.unit_list, name='unit_list'),
    path('units/create/', views.create_unit_with_participants, name='create_unit'),
    path('units/<int:unit_id>/edit/', views.edit_unit_with_participants, name='edit_unit'),
    path('participants/', views.participant_list, name='participant_list'),
]
