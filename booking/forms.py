from django import forms
from .models import Coach, Event, Booking
from django.forms import DateField
from django.forms.widgets import DateInput, CheckboxSelectMultiple
from datetime import date, timedelta
from company.models import Venue

# This form is used for the coach to create or edit an event
class EventForm(forms.ModelForm):

    venue = forms.ModelChoiceField(
        queryset=Venue.objects.all(),
        widget=forms.Select(attrs={'class': 'form-control'}),
        label="Venue",
        required=True
    )
    class Meta:
        model = Event
        fields = ['coach', 'event_name', 'description', 'date_of_event',
                  'venue','capacity', 'start_time', 'end_time', 'status']
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
        def __init__(self, *args, **kwargs):
            user = kwargs.pop('user', None)  # Extract the user from kwargs
            super().__init__(*args, **kwargs)
            if user:
                try:
                    coach = Coach.objects.get(user=user)  # Get the coach associated with the user
                    # Filter venues by the coach's company
                    self.fields['venue'].queryset = Venue.objects.filter(company=coach.company)
                except Coach.DoesNotExist:
                    # Handle the case where the user is not a coach.
                    self.fields['venue'].queryset = Venue.objects.none()

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
    venue = forms.ModelChoiceField(
        queryset=Venue.objects.all(),
        widget=forms.Select(attrs={'class': 'form-control'}),
        label="Venue",
        required=True
    )

    class Meta:
        model = Event
        fields = ['coach', 'event_name', 'description', 'date_of_event', 'venue',
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
        def __init__(self, *args, **kwargs):
            user = kwargs.pop('user', None)  # Extract the user from kwargs
            super().__init__(*args, **kwargs)
            if user:
                try:
                    coach = Coach.objects.get(user=user)  # Get the coach associated with the user
                    # Filter venues by the coach's company
                    self.fields['venue'].queryset = Venue.objects.filter(company=coach.company)
                except Coach.DoesNotExist:
                    # Handle the case where the user is not a coach.
                    self.fields['venue'].queryset = Venue.objects.none()
