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

# the multievent form is used to create multiple events at once
# and is used by the coach to create events

class MultiEventForm(forms.ModelForm):
    frequency = forms.IntegerField(
        min_value=1,
        label='Number of repetitions',
        widget=forms.NumberInput(attrs={'class': 'form-control', 'min': 1}),
        required=True
    )
    gap = forms.IntegerField(
        min_value=0,
        initial=15,
        label='Gap (minutes)',
        widget=forms.NumberInput(attrs={'class': 'form-control', 'min': 0}),
        required=True
    )
    event_details = forms.CharField(
        widget=forms.Textarea(
            attrs={'rows': 3, 'placeholder': 'Enter start-end times, one per line (e.g., 07:45-08:30)',
                   'class': 'form-control'}),
        label='Event Times',
        help_text='Format: HH:MM-HH:MM per line',
        required=True
    )

    class Meta:
        model = Event
        fields = ['coach', 'event_name', 'description', 'date_of_event',
                  'capacity', 'status', 'frequency', 'gap',
                  'event_details']  # Define the order here.
        widgets = {
            'coach': forms.Select(attrs={'class': 'form-control'}),
            'event_name': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control'}),
            'date_of_event': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'capacity': forms.NumberInput(attrs={'class': 'form-control',
                                                 'min': 1}),
            'status': forms.Select(attrs={'class': 'form-control'}),
        }
