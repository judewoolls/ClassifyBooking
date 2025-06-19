from django.test import TestCase
from django.contrib.auth.models import User
from .forms import EventForm
from .models import Coach, Event

from company.models import Company, Venue, Coach
from django.contrib.auth.models import User

class EventFormTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='formuser', password='pass1234')

        self.company = Company.objects.create(
            name='Test Gym Co',
            manager=self.user,
            address='321 Form St',
            city='Formville',
            postcode='FM123',
            phone_number='01234567891',
            email='form@gym.com',
            website='http://formgym.com'
        )

        self.venue = Venue.objects.create(name='Form Venue', company=self.company)
        self.coach = Coach.objects.create(coach=self.user, company=self.company)

    def test_event_form_valid(self):
        form_data = {
            'event_name': 'Form Test',
            'date_of_event': '2025-06-30',
            'coach': self.coach.pk,
            'status': 0,
            'description': 'Testing form',
            'venue': self.venue.pk,
            'start_time': '10:00',
            'end_time': '11:00',
            'capacity': 10,
        }
        form = EventForm(data=form_data)
        self.assertTrue(form.is_valid())
