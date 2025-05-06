from django.urls import path
from . import views

urlpatterns = [
    path('', views.logbook_view, name='open_log'),
    path('delete_score/<int:score_id>/',
         views.delete_score, name='delete_score'),
    path('edit_score/<int:score_id>/', views.edit_score, name='edit_score'),
]
