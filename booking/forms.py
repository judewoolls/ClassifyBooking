from django import forms
from .models import Event, TemplateEvent, Day
from django.forms import DateField
from django.forms.widgets import DateInput, CheckboxSelectMultiple
from datetime import date, timedelta
from company.models import Venue, Coach
import logging
from django.db import connection
# This form is used for the coach to create or edit an event

logger = logging.getLogger(__name__)


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
                  'venue', 'capacity', 'start_time', 'end_time', 'status']
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
        user = kwargs.pop('user', None)
        request = kwargs.pop('request', None)
        super().__init__(*args, **kwargs)

        if user:
            logger.debug(f"EventForm __init__ called with user: {user}")
            try:
                coach = Coach.objects.get(coach=user)
                self.fields['coach'].queryset = Coach.objects.filter(id=coach.id)
                self.fields['coach'].initial = coach.id

                self.fields['venue'].queryset = Venue.objects.filter(company=coach.company)
                self.fields['coach'].queryset = Coach.objects.filter(company=coach.company)

                logger.debug(f"Coach object: {coach}")
                logger.debug(f"Coach company: {coach.company}")
                logger.debug(f"coach queryset: {self.fields['coach'].queryset.query}")
                logger.debug(f"venue queryset: {self.fields['venue'].queryset.query}")
            except Coach.DoesNotExist:
                logger.warning(f"Coach.DoesNotExist for user: {user}")
                self.fields['venue'].queryset = Venue.objects.none()
                self.fields['coach'].queryset = Coach.objects.none()
        else:
            logger.warning("User is None in EventForm __init__")

        self.user = user
        self.request = request



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
        queryset=Venue.objects.none(),  # Default to none
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
                coach = Coach.objects.get(coach=user)  # Get the coach associated with the user
                # Filter venues by the coach's company
                self.fields['venue'].queryset = Venue.objects.filter(company=coach.company)
                self.fields['coach'].queryset = Coach.objects.filter(company=coach.company)
            except Coach.DoesNotExist:
                # Handle the case where the user is not a coach.
                self.fields['venue'].queryset = Venue.objects.none()


class TemplateEventForm(forms.ModelForm):
    venue = forms.ModelChoiceField(
        queryset=Venue.objects.all(),
        widget=forms.Select(attrs={'class': 'form-control'}),
        label="Venue",
        required=True
    )

    class Meta:
        model = TemplateEvent
        fields = ['coach', 'event_name', 'description', 'day_of_week',
                  'venue', 'capacity', 'start_time', 'end_time']
        widgets = {
            'coach': forms.Select(attrs={'class': 'form-control'}),
            'event_name': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control'}),
            'day_of_week': forms.Select(attrs={'class': 'form-control'}),
            'venue': forms.Select(attrs={'class': 'form-control'}),
            'capacity': forms.NumberInput(attrs={'class': 'form-control',
                                                 'min': 1}),
            'start_time': forms.TimeInput(attrs={'class': 'form-control'}),
            'end_time': forms.TimeInput(attrs={'class': 'form-control'}),
        }
    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        day_id = kwargs.pop('day_id', None)
        super().__init__(*args, **kwargs)

        if user:
            try:
                coach = Coach.objects.get(coach=user)
                self.fields['coach'].queryset = Coach.objects.filter(id=coach.id)
                self.fields['coach'].initial = coach.id

                self.fields['venue'].queryset = Venue.objects.filter(company=coach.company)
                self.fields['venue'].initial = Venue.objects.filter(company=coach.company).first()
                self.fields['coach'].queryset = Coach.objects.filter(company=coach.company)

                self.fields['day_of_week'].queryset = Day.objects.filter(id=day_id)
                self.fields['day_of_week'].initial = day_id

            except Coach.DoesNotExist:
                self.fields['venue'].queryset = Venue.objects.none()
                self.fields['coach'].queryset = Coach.objects.none()
        else:
            self.fields['venue'].queryset = Venue.objects.none()
            self.fields['coach'].queryset = Coach.objects.none()