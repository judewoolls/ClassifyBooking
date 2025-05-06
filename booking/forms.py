from django import forms
from .models import Coach, Event, Booking


# This form is used for the coach to create or edit an event
class EventForm(forms.ModelForm):
    class Meta:
        model = Event
        fields = ['coach', 'event_name', 'description', 'date_of_event',
                  'capacity', 'start_time', 'end_time', 'status']
        widgets = {
            'coach': forms.Select(attrs={'class': 'form-control'}),
            'event_name': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control'}),
            'date_of_event': forms.DateInput(attrs={'class': 'form-control'}),
            'capacity': forms.NumberInput(attrs={'class': 'form-control',
                                                 'min': 1}),
            'start_time': forms.TimeInput(attrs={'class': 'form-control'}),
            'end_time': forms.TimeInput(attrs={'class': 'form-control'}),
            'status': forms.Select(attrs={'class': 'form-control'}),
        }
