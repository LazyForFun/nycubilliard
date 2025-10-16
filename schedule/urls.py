"""billiard URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/3.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.urls import path
from . import views

urlpatterns = [
    path('Home', views.Home.as_view(), name='Home'),
    path('Login', views.LoginView.as_view(), name='Login'),
    path('Logout', views.LogoutView.as_view(), name='Logout'),
    path('MatchDetailView/<int:pk>', views.MatchDetailView.as_view(), name='MatchDetailView'),
    path('AnnouncementCreateView', views.AnnouncementCreateView.as_view(), name='AnnouncementCreateView'),
    path('AnnouncementUpdateView/<int:pk>', views.AnnouncementUpdateView.as_view(), name='AnnouncementUpdateView'),
    path("AnnouncementsDeleteView/<int:pk>", views.AnnouncementDeleteView.as_view(), name="AnnouncementDeleteView"),
    path('AnnouncementListView', views.AnnouncementListView.as_view(), name='AnnouncementListView'),
    path('AnnouncementDetailView/<int:pk>', views.AnnouncementDetailView.as_view(), name='AnnouncementDetailView'),
    path('TournamentDetailView/<int:pk>', views.TournamentDetailView.as_view(), name='TournamentDetailView'),
    path('TournamentCreateView', views.TournamentCreateView.as_view(), name='TournamentCreateView'),
    path('TournamentListView', views.TournamentListView.as_view(), name='TournamentListView'),
    path('TournamentDeleteView/<int:pk>', views.TournamentDeleteView.as_view(), name='TournamentDeleteView')
    
]
