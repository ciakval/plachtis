from django.urls import path
from . import views

app_name = 'SkaRe'

urlpatterns = [
    path('', views.home, name='home'),
    path('register/', views.register, name='register'),
    path('login/', views.user_login, name='login'),
    path('logout/', views.user_logout, name='logout'),
    
    # Group and Participant management
    path('groups/', views.group_list, name='group_list'),
    path('groups/create/', views.create_group_with_participants, name='create_group'),
    path('participants/', views.participant_list, name='participant_list'),
]
