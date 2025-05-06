from . import views
from django.urls import path

urlpatterns = [
    path('book_event/<int:event_id>/', views.book_event, name='book_event'),
    path('cancel_event/<int:event_id>/',
         views.cancel_event, name='cancel_event'),
    path('delete_event/<int:event_id>/', views.delete_event,
         name='delete_event'),
    path('create_event/', views.create_event, name='create_event'),
    path('edit_event/<int:event_id>/', views.edit_event, name='edit_event'),
    path('<str:date>/', views.event_search, name='event_search'),
    path('<str:date>/<int:id>/', views.event_detail, name='event_detail'),
]
