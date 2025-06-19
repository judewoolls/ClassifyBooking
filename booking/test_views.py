from django.test import TestCase
from django.urls import reverse
from django.contrib.auth.models import User
from django.utils.timezone import make_aware

from datetime import date, time, timedelta

from .models import Event, Booking
from .forms import EventForm
from company.models import Coach, Company, Venue, Token
import html

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

# tests for event booking


class BookEventViewTest(TestCase):
    def setUp(self):
        # Create user, company, coach, venue
        self.user = User.objects.create_user(username='testuser', password='testpass')
        self.company = Company.objects.create(name='Test Co', manager=self.user)
        self.coach = Coach.objects.create(coach=self.user, company=self.company)
        self.venue = Venue.objects.create(name='Main Hall', company=self.company)

        self.event = Event.objects.create(
            event_name="Test Class",
            date_of_event=date.today() + timedelta(days=1),  # future event
            coach=self.coach,
            status=0,
            description='Test Desc',
            venue=self.venue,
            start_time=time(10, 0),
            end_time=time(11, 0),
            capacity=2
        )

        self.token = Token.objects.create(user=self.user, company=self.company, used=False)

    def test_successful_booking(self):
        self.client.login(username='testuser', password='testpass')
        response = self.client.post(reverse('book_event', args=[self.event.id]))
        self.assertRedirects(response, reverse('event_search', args=[self.event.date_of_event]))
        self.assertTrue(Booking.objects.filter(user=self.user, event=self.event).exists())
        self.assertTrue(Token.objects.get(pk=self.token.pk).used)

    def test_event_in_past(self):
        self.event.status = 1
        self.event.save()
        self.client.login(username='testuser', password='testpass')
        response = self.client.post(reverse('book_event', args=[self.event.id]), follow=True)

        self.assertEqual(response.status_code, 200)
        self.assertIn(
    "can't book after the class has started",
    html.unescape(response.content.decode().lower())
)


    def test_event_full(self):
        # Fill event
        other_user = User.objects.create_user(username='other', password='pass')
        Booking.objects.create(user=other_user, event=self.event)
        Booking.objects.create(user=self.user, event=self.event)

        self.client.login(username='testuser', password='testpass')
        response = self.client.post(reverse('book_event', args=[self.event.id]), follow=True)
        self.assertContains(response, "Event is full")

    def test_user_already_booked(self):
        Booking.objects.create(user=self.user, event=self.event)

        self.client.login(username='testuser', password='testpass')
        response = self.client.post(reverse('book_event', args=[self.event.id]), follow=True)
        self.assertContains(response, "You have already booked this event")

    def test_no_token_available(self):
        self.token.used = True
        self.token.save()

        self.client.login(username='testuser', password='testpass')
        response = self.client.post(reverse('book_event', args=[self.event.id]), follow=True)

        self.assertEqual(response.status_code, 200)
        self.assertIn(
            "don't have any available tokens",
            html.unescape(response.content.decode().lower())
        )