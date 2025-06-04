from . import views
from django.urls import path

urlpatterns = [
    path('company_dashboard/', views.company_dashboard, name='company_dashboard'),
    path('change_details/', views.change_company_details, name='change_company_details'),
    path('add_coach/', views.add_coach, name='add_coach'),
    path('remove_coach/', views.remove_coach, name='remove_coach'),
    path('remove_client/<int:client_id>/', views.remove_client, name="remove_client"),
    path('view_bookings/', views.view_bookings, name='view_bookings'),
    path('delete_booking/<int:booking>', views.delete_booking, name='delete_booking'),
    path('view_clients/', views.view_clients, name='view_clients'),
    path('client_details/<int:client_id>/', views.client_details, name='client_details'),
]