from . import views
from django.urls import path

urlpatterns = [
    path('company_dashboard/', views.company_dashboard, name='company_dashboard'),
    path('change_details/', views.change_company_details, name='change_company_details'),
]