from django.test import TestCase
from django.contrib.auth.models import User
from .forms import EventForm
from .models import Coach, Event

class EventFormTest(TestCase):
    def setUp(self):
        # Create a mock user and a coach for testing
        self.user = User.objects.create(username='testuser', password='testpass')
        self.coach = Coach.objects.create(coach=self.user)

    def test_event_form_valid(self):
        form_data = {
            'coach': self.coach.id,
            'event_name': 'Test Event',
            'description': 'This is a test event.',
            'date_of_event': '2023-12-31',
            'capacity': 10,
            'start_time': '10:00',
            'end_time': '12:00',
            'status': 0,
        }
        form = EventForm(data=form_data)
        self.assertTrue(form.is_valid())