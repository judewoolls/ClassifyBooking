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
            'date_of_event': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'capacity': forms.NumberInput(attrs={'class': 'form-control',
                                                 'min': 1}),
            'start_time': forms.TimeInput(attrs={'class': 'form-control'}),
            'end_time': forms.TimeInput(attrs={'class': 'form-control'}),
            'status': forms.Select(attrs={'class': 'form-control'}),
        }

# the multievent form is used to create multiple events at once
# and is used by the coach to create events
class MultiEventForm(forms.ModelForm):
    start_time = forms.TimeField(
        label='Start Time',
        widget=forms.TimeInput(attrs={'class': 'form-control'}),
        required=True
    )
    end_time = forms.TimeField(
        label='End Time',
        widget=forms.TimeInput(attrs={'class': 'form-control'}),
        required=True
    )
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

    class Meta:
        model = Event
        fields = ['coach', 'event_name', 'description', 'date_of_event',
                  'capacity', 'status', 'start_time', 'end_time', 'frequency', 'gap']
        widgets = {
            'coach': forms.Select(attrs={'class': 'form-control'}),
            'event_name': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control'}),
            'date_of_event': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'capacity': forms.NumberInput(attrs={'class': 'form-control',
                                                 'min': 1}),
            'status': forms.Select(attrs={'class': 'form-control'}),
        }
