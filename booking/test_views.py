from django.test import TestCase
from django.urls import reverse
from django.contrib.auth.models import User
from django.utils.timezone import make_aware

from datetime import date, time, timedelta

from .models import Event, Booking
from .forms import EventForm
from company.models import Coach, Company, Venue, Token


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




# tests for the event search


class EventSearchViewTest(TestCase):

    def setUp(self):
        self.user = User.objects.create_user(username='viewuser', password='pass1234')

        self.company = Company.objects.create(
            name='Search Co',
            manager=self.user,
            address='1 Event St',
            city='Searchville',
            postcode='SE123',
            phone_number='01111111111',
            email='search@co.com',
            website='http://searchco.com'
        )

        self.venue = Venue.objects.create(name='Search Venue', company=self.company)
        self.coach = Coach.objects.create(coach=self.user, company=self.company)

        # Add company to user's profile if your Profile model has it
        self.user.profile.company = self.company
        self.user.profile.save()

        self.today = date.today()

        self.event = Event.objects.create(
            event_name="Searchable Event",
            date_of_event=self.today,
            coach=self.coach,
            status=0,
            description='Test event',
            venue=self.venue,
            start_time=time(9, 0),
            end_time=time(10, 0),
            capacity=10
        )

    def test_login_required(self):
        url = reverse('event_search', args=[self.today.strftime('%Y-%m-%d')])
        response = self.client.get(url)
        self.assertRedirects(response, f'/accounts/login/?next={url}')

    def test_invalid_date_returns_400(self):
        self.client.login(username='viewuser', password='pass1234')
        response = self.client.get(reverse('event_search', args=["not-a-date"]))
        self.assertEqual(response.status_code, 400)
        self.assertIn(b"Invalid date format", response.content)

    def test_valid_date_shows_events(self):
        self.client.login(username='viewuser', password='pass1234')
        response = self.client.get(reverse('event_search', args=[self.today.strftime('%Y-%m-%d')]))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'booking/index.html')
        self.assertIn('events', response.context)
        self.assertEqual(len(response.context['events']), 1)
        self.assertEqual(response.context['events'][0], self.event)

    def test_context_variables(self):
        Token.objects.create(user=self.user, company=self.company, used=False)

        self.client.login(username='viewuser', password='pass1234')
        response = self.client.get(reverse('event_search', args=[self.today.strftime('%Y-%m-%d')]))

        self.assertEqual(response.context['current_date'], self.today)
        self.assertEqual(response.context['previous_date'], self.today - timedelta(days=1))
        self.assertEqual(response.context['next_date'], self.today + timedelta(days=1))
        self.assertEqual(response.context['tokens'], 1)
        self.assertIn('is_coach', response.context)