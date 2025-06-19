from django.test import TestCase
from django.urls import reverse
from django.contrib.auth.models import User
from django.utils.timezone import make_aware
from datetime import date, time, timedelta
import html

from company.models import Coach, Company, Venue, Token
from booking.models import Event, Booking


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
        self.assertIn(
            "event is full",
            html.unescape(response.content.decode().lower())
        )

    def test_user_already_booked(self):
        Booking.objects.create(user=self.user, event=self.event)

        self.client.login(username='testuser', password='testpass')
        response = self.client.post(reverse('book_event', args=[self.event.id]), follow=True)
        self.assertIn(
            "you have already booked this event",
            html.unescape(response.content.decode().lower())
        )

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

    def test_booking_requires_login(self):
        """Test that booking an event requires the user to be logged in."""
        response = self.client.post(reverse('book_event', args=[self.event.id]))
        self.assertRedirects(response, f'/accounts/login/?next={reverse("book_event", args=[self.event.id])}')

    def test_booking_invalid_event_id(self):
        """Test that booking an event with an invalid ID returns a 404."""
        self.client.login(username='testuser', password='testpass')
        response = self.client.post(reverse('book_event', args=[9999]))  # Non-existent event ID
        self.assertEqual(response.status_code, 404)

    def test_booking_event_with_no_capacity(self):
        """Test that booking an event with no capacity shows an error."""
        self.event.capacity = 0
        self.event.save()

        self.client.login(username='testuser', password='testpass')
        response = self.client.post(reverse('book_event', args=[self.event.id]), follow=True)

        self.assertIn(
            "event is full",
            html.unescape(response.content.decode().lower())
        )


    def test_booking_with_multiple_tokens(self):
        """Test that booking an event uses the correct token when multiple tokens are available."""
        Token.objects.create(user=self.user, company=self.company, used=False)  # Additional token

        self.client.login(username='testuser', password='testpass')
        response = self.client.post(reverse('book_event', args=[self.event.id]), follow=True)

        self.assertRedirects(response, reverse('event_search', args=[self.event.date_of_event]))
        self.assertTrue(Token.objects.filter(user=self.user, company=self.company, used=True).count(), 1)

    def test_booking_event_with_overlapping_times(self):
        """Test that booking an event with overlapping times fails."""
        overlapping_event = Event.objects.create(
            event_name="Overlapping Event",
            date_of_event=self.event.date_of_event,
            coach=self.coach,
            status=0,
            description='Test Desc',
            venue=self.venue,
            start_time=self.event.start_time,
            end_time=self.event.end_time,
            capacity=2
        )
        Booking.objects.create(user=self.user, event=overlapping_event)

        self.client.login(username='testuser', password='testpass')
        response = self.client.post(reverse('book_event', args=[self.event.id]), follow=True)

        self.assertIn(
            "you cannot book overlapping events",
            html.unescape(response.content.decode().lower())
        )


    def test_booking_with_used_token(self):
        """Test that booking an event with a used token fails."""
        self.token.used = True
        self.token.save()

        self.client.login(username='testuser', password='testpass')
        response = self.client.post(reverse('book_event', args=[self.event.id]), follow=True)

        self.assertIn(
            "you don't have any available tokens",
            html.unescape(response.content.decode().lower())
        )
#tests for cancelling bookings

class CancelEventViewTest(TestCase):
    def setUp(self):
        # Create user, company, coach, venue, and event
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

        self.token = Token.objects.create(user=self.user, company=self.company, used=True)
        self.booking = Booking.objects.create(user=self.user, event=self.event)
        self.token.booking = self.booking
        self.token.save()

    def test_cancel_booking_successfully(self):
        """Test that a booking can be canceled successfully and the token is refunded."""
        self.client.login(username='testuser', password='testpass')
        response = self.client.post(reverse('cancel_event', args=[self.event.id]), follow=True)

        self.assertRedirects(response, reverse('event_search', args=[self.event.date_of_event]))
        self.assertFalse(Booking.objects.filter(user=self.user, event=self.event).exists())
        self.assertFalse(Token.objects.get(pk=self.token.pk).used)
        self.assertIsNone(Token.objects.get(pk=self.token.pk).booking)
        self.assertIn(
            "booking cancelled successfully and token refunded.",
            html.unescape(response.content.decode().lower())
        )

    def test_cancel_booking_no_token_found(self):
        """Test that canceling a booking without a token linked shows an error."""
        self.token.used = False
        self.token.booking = None
        self.token.save()

        self.client.login(username='testuser', password='testpass')
        response = self.client.post(reverse('cancel_event', args=[self.event.id]), follow=True)

        self.assertRedirects(response, reverse('event_search', args=[self.event.date_of_event]))
        self.assertIn(
            "no token found for this booking to refund.",
            html.unescape(response.content.decode().lower())
        )

    def test_cancel_booking_no_booking_found(self):
        """Test that canceling a booking that doesn't exist shows an error."""
        self.booking.delete()

        self.client.login(username='testuser', password='testpass')
        response = self.client.post(reverse('cancel_event', args=[self.event.id]), follow=True)

        self.assertRedirects(response, reverse('event_search', args=[self.event.date_of_event]))
        self.assertIn(
            "you do not have a booking for this event",
            html.unescape(response.content.decode().lower())
        )

    def test_cancel_booking_event_in_past(self):
        """Test that canceling a booking for an event in the past shows an error."""
        self.event.status = 1  # Event has started
        self.event.save()

        self.client.login(username='testuser', password='testpass')
        response = self.client.post(reverse('cancel_event', args=[self.event.id]), follow=True)

        self.assertRedirects(response, reverse('event_search', args=[self.event.date_of_event]))
        self.assertIn(
            "you can't cancel a booking after the class has started.",
            html.unescape(response.content.decode().lower())
        )

    def test_cancel_booking_requires_login(self):
        """Test that canceling a booking requires the user to be logged in."""
        response = self.client.post(reverse('cancel_event', args=[self.event.id]))
        self.assertRedirects(response, f'/accounts/login/?next={reverse("cancel_event", args=[self.event.id])}')

# tests for deleting an event

class DeleteEventViewTest(TestCase):

    def setUp(self):
        self.user = User.objects.create_user(username='coach', password='testpass')
        self.company = Company.objects.create(name='Test Co', manager=self.user)
        self.coach = Coach.objects.create(coach=self.user, company=self.company)
        self.event = Event.objects.create(
            event_name='Test Event',
            date_of_event=date.today(),
            start_time='12:00',
            end_time='13:00',
            venue=Venue.objects.create(name='Test Venue', company=self.company),
            status=0,  # Future event
            description='Test Description',
            capacity=10,
            coach=self.coach,
        )
        self.url = reverse('delete_event', args=[self.event.id])
        self.redirect_url = reverse('event_search', kwargs={'date': self.event.date_of_event})

    def test_redirects_if_not_logged_in(self):
        response = self.client.post(self.url)
        self.assertNotEqual(response.status_code, 200)
        self.assertRedirects(response, f'/accounts/login/?next={self.url}')

    def test_get_request_does_not_delete_event(self):
        self.client.login(username='coach', password='testpass')
        response = self.client.get(self.url)
        self.assertRedirects(response, self.redirect_url)
        self.assertTrue(Event.objects.filter(id=self.event.id).exists())

    def test_post_request_deletes_event(self):
        self.client.login(username='coach', password='testpass')
        response = self.client.post(self.url, follow=True)
        self.assertRedirects(response, self.redirect_url)
        self.assertFalse(Event.objects.filter(id=self.event.id).exists())

    def test_success_message_displayed(self):
        self.client.login(username='coach', password='testpass')
        response = self.client.post(self.url, follow=True)
        messages = list(response.context['messages'])
        self.assertTrue(any("Event deleted successfully" in str(m) for m in messages))