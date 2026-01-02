"""
URLs для приложения core.
"""
from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('competitors/', views.competitors, name='competitors'),
    path('pricing/', views.pricing, name='pricing'),
    path('reports/', views.reports, name='reports'),
]