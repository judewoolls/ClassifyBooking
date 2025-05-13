from . import views
from django.urls import path

urlpatterns = [
    path('company_dashboard/', views.company_dashboard, name='company_dashboard'),
]