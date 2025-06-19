from django.test import TestCase
from django.urls import reverse
from django.contrib.auth.models import User
from django.utils.timezone import make_aware

from datetime import date, time

from .models import Event, Booking
from .forms import EventForm
from company.models import Coach, Company, Venue


class EventDetailViewTest(TestCase):

    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='pass1234')

        self.company = Company.objects.create(
            name='Test Gym',
            manager=self.user,
            address='123 Test St',
            city='Testville',
            postcode='TE57GY',
            phone_number='01234567890',
            email='test@gym.com',
            website='http://testgym.com'
        )

        self.venue = Venue.objects.create(name='The Gym', company=self.company)
        self.coach = Coach.objects.create(coach=self.user, company=self.company)

        self.event_date = date.today()

        self.event = Event.objects.create(
            event_name="Test Event",
            date_of_event=self.event_date,
            coach=self.coach,
            status=0,
            description='Description',
            venue=self.venue,
            start_time=time(10, 0),
            end_time=time(11, 0),
            capacity=10
        )

    def test_event_detail_requires_login(self):
        url = reverse('event_detail', args=[self.event_date.strftime('%Y-%m-%d'), self.event.id])
        response = self.client.get(url)
        self.assertRedirects(response, f'/accounts/login/?next={url}')

    def test_event_detail_renders_correct_template_and_context(self):
        self.client.login(username='testuser', password='pass1234')
        url = reverse('event_detail', args=[self.event_date.strftime('%Y-%m-%d'), self.event.id])
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'booking/event_detail.html')
        self.assertEqual(response.context['event'], self.event)
        self.assertTrue(response.context['is_coach'])  # since the user is a coach
