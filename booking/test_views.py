from django.test import TestCase
from django.urls import reverse
from django.contrib.auth.models import User
from django.utils.timezone import make_aware
from datetime import date, time, timedelta
import html
from django.contrib.messages import get_messages

from company.models import Coach, Company, Venue, Token, UserProfile
from booking.models import Event, Booking, Day, TemplateEvent

from booking.forms import EventForm, TemplateEventForm


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


#tests for creating multi events

class CreateMultiEventViewTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='testpass')
        self.company = Company.objects.create(name='Test Co', manager=self.user)
        self.coach = Coach.objects.create(coach=self.user, company=self.company)
        self.venue = Venue.objects.create(name='Main Hall', company=self.company)
        self.url = reverse('create_multi_event')

    def test_create_multi_event_redirects_on_success(self):
        """Form with valid data should redirect after creating events."""
        self.client.login(username='testuser', password='testpass')
        data = {
            'date_of_event': date.today().strftime('%Y-%m-%d'),
            'venue': self.venue.pk,
            'start_time': '10:00',
            'end_time': '11:00',
            'frequency': 2,
            'gap': 30,
            'event_name': 'Test Event',
            'description': 'Description',
            'capacity': 10,
            'status': 0,
            'coach': self.coach.pk,  # Ensure coach is set
        }
        response = self.client.post(self.url, data=data)
        self.assertEqual(response.status_code, 302)  # Redirect
        self.assertEqual(Event.objects.count(), 2)

    def test_create_multi_event_with_invalid_form(self):
        """Missing required fields should return the form with errors."""
        self.client.login(username='testuser', password='testpass')
        data = {
            'date_of_event': '',
            'venue': self.venue.pk,
            'start_time': '10:00',
            'end_time': '11:00',
            'frequency': 2,
            'gap': 30,
            'event_name': 'Test Event',
            'description': 'Description',
            'capacity': 10,
            'status': 0,
            'coach': self.coach.pk,  # Ensure coach is set
        }
        response = self.client.post(self.url, data=data)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "This field is required.")
        self.assertEqual(Event.objects.count(), 0)

    def test_create_multi_event_no_login(self):
        """Unauthenticated users should be redirected."""
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.url.startswith(reverse('account_login')))

    def test_create_multi_event_no_coach(self):
        """Users who are not coaches should be redirected."""
        other_user = User.objects.create_user(username='noncoach', password='testpass')
        self.client.login(username='noncoach', password='testpass')
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('event_search', args=[date.today()]))

    def test_create_multi_event_with_zero_frequency(self):
        """Frequency of 0 should not create events."""
        self.client.login(username='testuser', password='testpass')
        data = {
            'date_of_event': date.today().strftime('%Y-%m-%d'),
            'venue': self.venue.pk,
            'start_time': '10:00',
            'end_time': '11:00',
            'frequency': 0,
            'gap': 30,
            'event_name': 'Test Event',
            'description': 'Description',
            'capacity': 10,
            'status': 0,
            'coach': self.coach.pk,  # Ensure coach is set
        }
        response = self.client.post(self.url, data=data)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Form is invalid")  # Assuming you show this
        self.assertEqual(Event.objects.count(), 0)



# tests for duplicating an event


class DuplicateEventViewTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='coachuser', password='testpass')
        self.company = Company.objects.create(name='Test Gym', manager=self.user)
        self.venue = Venue.objects.create(name='Main Gym', company=self.company)
        self.coach = Coach.objects.create(coach=self.user, company=self.company)

        self.original_date = date.today()
        self.event = Event.objects.create(
            coach=self.coach,
            event_name="Yoga",
            description="Morning yoga session",
            venue=self.venue,
            date_of_event=self.original_date,
            capacity=10,
            start_time=time(9, 0),
            end_time=time(10, 0),
            status=0,
        )

        self.url = reverse('duplicate_day_events', args=[self.original_date.strftime("%Y-%m-%d")])

    def test_redirect_if_not_logged_in(self):
        response = self.client.get(self.url)
        self.assertRedirects(response, f'/accounts/login/?next={self.url}')

    def test_get_duplicate_event_page(self):
        self.client.login(username='coachuser', password='testpass')
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'booking/duplicate_events.html')
        self.assertContains(response, self.original_date.strftime("%Y-%m-%d"))

    def test_post_valid_date_array_duplicates_event(self):
        self.client.login(username='coachuser', password='testpass')
        new_dates = [
            (self.original_date + timedelta(days=1)).strftime("%Y-%m-%d"),
            (self.original_date + timedelta(days=2)).strftime("%Y-%m-%d"),
        ]
        response = self.client.post(self.url, {
            'dates-sent': ', '.join(new_dates)
        }, follow=True)

        self.assertRedirects(response, reverse('event_search', args=[self.original_date]))
        self.assertEqual(Event.objects.filter(event_name="Yoga").count(), 3)  # original + 2 copies
        self.assertTrue(Event.objects.filter(date_of_event=new_dates[0]).exists())
        self.assertTrue(Event.objects.filter(date_of_event=new_dates[1]).exists())

    def test_post_missing_dates_sent(self):
        self.client.login(username='coachuser', password='testpass')
        response = self.client.post(self.url, {}, follow=True)
        self.assertRedirects(response, reverse('event_search', args=[self.original_date]))
        messages = list(response.context['messages'])
        self.assertEqual(len(messages), 1)
        self.assertIn("Invalid date input", messages[0].message)

    def test_invalid_url_date_returns_400(self):
        self.client.login(username='coachuser', password='testpass')
        bad_url = reverse('duplicate_day_events', args=["2024-99-99"])  # invalid date
        response = self.client.get(bad_url)
        self.assertEqual(response.status_code, 400)
        self.assertContains(response, "Invalid date format", status_code=400)


    def test_duplicate_only_own_company_events(self):
        # Create an event from another company
        other_user = User.objects.create_user(username='otheruser', password='pass')
        other_company = Company.objects.create(name='Other Gym', manager=other_user)
        other_coach = Coach.objects.create(coach=other_user, company=other_company)
        Event.objects.create(
            coach=other_coach,
            event_name="Pilates",
            description="Afternoon class",
            venue=self.venue,
            date_of_event=self.original_date,
            capacity=5,
            start_time=time(14, 0),
            end_time=time(15, 0),
            status=0
        )

        self.client.login(username='coachuser', password='testpass')
        new_date = (self.original_date + timedelta(days=1)).strftime("%Y-%m-%d")
        response = self.client.post(self.url, {'dates-sent': new_date}, follow=True)

        # Only the original user's event should be duplicated
        yoga_events = Event.objects.filter(event_name="Yoga")
        pilates_events = Event.objects.filter(event_name="Pilates")
        self.assertEqual(yoga_events.count(), 2)  # original + 1 copy
        self.assertEqual(pilates_events.count(), 1)  # not duplicated


# tests for edit event


class EditEventViewTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='testpass')
        self.client.login(username='testuser', password='testpass')
        self.company = Company.objects.create(name='Test Gym', manager=self.user)
        self.coach = Coach.objects.create(coach=self.user, company=self.company)
        self.venue = Venue.objects.create(name='Main Gym', company=self.company)
        self.event = Event.objects.create(
            event_name="Test Class",
            date_of_event=date.today(),
            start_time=time(10, 0),
            end_time=time(11, 0),
            venue = self.venue,
            capacity=10,
            coach=self.coach,  # adjust based on your model
            status=0,  # Future event
        )
        self.url = reverse('edit_event', args=[self.event.id])

    def test_get_edit_event_page_returns_200(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "booking/edit_event.html")
        self.assertContains(response, "Test Class")

    def test_redirects_if_not_logged_in(self):
        self.client.logout()
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 302)
        self.assertIn('/accounts/login/', response.url)

    def test_invalid_event_id_returns_404(self):
        response = self.client.get(reverse('edit_event', args=[9999]))
        self.assertEqual(response.status_code, 404)

    def test_form_prefilled_with_event_data(self):
        response = self.client.get(self.url)
        form = response.context['form']
        self.assertIsInstance(form, EventForm)
        self.assertEqual(form.instance, self.event)

    def test_post_valid_data_updates_event_and_redirects(self):
        updated_data = {
            'event_name': "Updated Class",
            'description': "New description here",   # required field
            'date_of_event': self.event.date_of_event.strftime('%Y-%m-%d'),  # format as string if needed
            'start_time': self.event.start_time.strftime('%H:%M:%S'),       # format as string
            'end_time': self.event.end_time.strftime('%H:%M:%S'),           # format as string
            'capacity': 20,
            'coach': self.user.pk,        # must be a valid user id in DB
            'venue': self.venue.pk,       # must be a valid venue id in DB
            'status': self.event.status,  # or a valid status value
        }
        response = self.client.post(self.url, updated_data, follow=True)
        self.assertContains(response, "Event updated successfully")
        self.event.refresh_from_db()
        self.assertEqual(self.event.event_name, "Updated Class")
        self.assertEqual(self.event.capacity, 20)
        self.assertRedirects(response, reverse('event_search', args=[self.event.date_of_event]))

    def test_post_invalid_data_returns_200_and_shows_errors(self):
        invalid_data = {
            'event_name': "",  # Required field
            'date_of_event': "",
            'start_time': "",
            'end_time': "",
            'capacity': "",
            'coach': "",
        }
        response = self.client.post(self.url, invalid_data)
        self.assertEqual(response.status_code, 200)
        self.assertFormError(response, "form", "event_name", "This field is required.")
        self.assertFormError(response, "form", "date_of_event", "This field is required.")

# tests for coach dashboard


class CoachDashboardViewTest(TestCase):

    def setUp(self):
        # Create user and company
        self.user = User.objects.create_user(username='coachuser', password='testpass')
        self.company = Company.objects.create(name="Test Company", manager=self.user)

        # Create coach linked to user and company
        self.coach = Coach.objects.create(coach=self.user, company=self.company)

        self.url = reverse('coach_dashboard')

    def test_redirect_if_not_coach(self):
        # Create a non-coach user
        non_coach_user = User.objects.create_user(username='normaluser', password='testpass')
        self.client.login(username='normaluser', password='testpass')

        response = self.client.get(self.url)
        self.assertRedirects(response, reverse('event_search', args=[date.today()]))

        # Check error message is in messages
        messages = list(get_messages(response.wsgi_request))
        self.assertTrue(any("not authorized" in m.message for m in messages))

    def test_dashboard_loads_for_coach(self):
        self.client.login(username='coachuser', password='testpass')
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "booking/coach_dashboard.html")
        self.assertIn('is_coach', response.context)
        self.assertTrue(response.context['is_coach'])
        self.assertIn('company', response.context)
        self.assertEqual(response.context['company'], self.company)

# this test case is for loading the schedule


class ScheduleViewTest(TestCase):

    def setUp(self):
        # Create user, company, coach
        self.user = User.objects.create_user(username='coachuser', password='testpass')
        self.company = Company.objects.create(name="Test Company", manager=self.user)
        self.coach = Coach.objects.create(coach=self.user, company=self.company)
        self.venue = Venue.objects.create(name='Main Gym', company=self.company)

        # Create a Day instance
        self.day = Day.objects.create(day="Monday")

        # Create some TemplateEvents for this coach and day
        self.event1 = TemplateEvent.objects.create(
            coach=self.coach,
            day_of_week=self.day,
            start_time=time(9, 0),
            end_time=time(10, 0),
            event_name="Morning Yoga",
            capacity=10,
            venue=self.venue
        )
        self.event2 = TemplateEvent.objects.create(
            coach=self.coach,
            day_of_week=self.day,
            start_time=time(11, 0),
            end_time=time(12, 0),
            event_name="Pilates",
            capacity=10,
            venue=self.venue
        )

        self.url = reverse('schedule', args=[self.day.id])

    def test_redirect_if_not_coach(self):
        non_coach_user = User.objects.create_user(username='normaluser', password='testpass')
        self.client.login(username='normaluser', password='testpass')

        response = self.client.get(self.url)
        self.assertRedirects(response, reverse('event_search', args=[date.today()]))

        messages = list(get_messages(response.wsgi_request))
        self.assertTrue(any("not authorized" in m.message for m in messages))

    def test_schedule_renders_correctly_for_coach(self):
        self.client.login(username='coachuser', password='testpass')

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "booking/schedule.html")

        # Check context variables
        self.assertIn('template_events', response.context)
        self.assertIn('is_coach', response.context)
        self.assertTrue(response.context['is_coach'])
        self.assertIn('day', response.context)
        self.assertEqual(response.context['day'], self.day)

        # Check the template_events are correct and ordered by start_time
        template_events = response.context['template_events']
        self.assertEqual(list(template_events), [self.event1, self.event2])


class AddTemplateEventViewTest(TestCase):

    def setUp(self):
        # User, company, coach, day and venue setup
        self.user = User.objects.create_user(username='coachuser', password='testpass')
        self.company = Company.objects.create(name="Test Gym", manager=self.user)
        self.coach = Coach.objects.create(coach=self.user, company=self.company)
        self.day = Day.objects.create(day="Tuesday")
        self.venue = Venue.objects.create(name="Main Hall", company=self.company)

        self.url = reverse('add_template_event', args=[self.day.id])

        self.valid_data = {
            'event_name': 'Spin Class',
            'description': 'High intensity cycling',
            'venue': self.venue,
            'start_time': '09:00',
            'end_time': '10:00',
            'capacity': 12,
        }

    def test_get_add_template_event_form(self):
        self.client.login(username='coachuser', password='testpass')
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'booking/template_event.html')
        self.assertIn('form', response.context)
        self.assertIn('day_id', response.context)
        self.assertEqual(response.context['day_id'], self.day.id)

    def test_post_valid_template_event_form_creates_event(self):
        self.client.login(username='coachuser', password='testpass')

        data = self.valid_data.copy()
        data['day_of_week'] = str(self.day.id)
        data['coach'] = str(self.coach.id)
        data['venue'] = str(self.venue.venue_id)  # Add this line!

        response = self.client.post(self.url, data)

        self.assertEqual(TemplateEvent.objects.count(), 1)
        event = TemplateEvent.objects.first()
        self.assertEqual(event.event_name, 'Spin Class')
        self.assertEqual(event.coach, self.coach)
        self.assertEqual(event.venue, self.venue)
        self.assertEqual(event.day_of_week, self.day)

        self.assertRedirects(response, reverse('schedule', args=[self.day.id]))
        messages = list(get_messages(response.wsgi_request))
        self.assertTrue(any("created successfully" in m.message for m in messages))

    def test_post_invalid_template_event_form_renders_errors(self):
        self.client.login(username='coachuser', password='testpass')

        invalid_data = self.valid_data.copy()
        invalid_data['event_name'] = ''  # Missing required field

        response = self.client.post(self.url, invalid_data)

        self.assertEqual(response.status_code, 200)
        self.assertFormError(response, 'form', 'event_name', 'This field is required.')

        self.assertEqual(TemplateEvent.objects.count(), 0)
        messages = list(get_messages(response.wsgi_request))
        self.assertTrue(any("problem with the form" in m.message for m in messages))

    def test_redirects_if_not_logged_in(self):
        response = self.client.get(self.url)
        login_url = reverse('account_login')
        self.assertRedirects(response, f'{login_url}?next={self.url}')

# tests for deleting templates


class DeleteTemplateEventViewTest(TestCase):
    def setUp(self):
        # Setup a coach and related data
        self.user = User.objects.create_user(username='coachuser', password='testpass')
        self.company = Company.objects.create(name="Test Gym", manager=self.user)
        self.coach = Coach.objects.create(coach=self.user, company=self.company)
        self.day = Day.objects.create(day="Tuesday")
        self.venue = Venue.objects.create(name="Main Hall", company=self.company)

        self.template_event = TemplateEvent.objects.create(
            event_name="Boxing",
            description="Heavy bag work",
            coach=self.coach,
            day_of_week=self.day,
            venue=self.venue,
            capacity=10,
            start_time=time(12, 0),
            end_time=time(13, 0)
        )

        self.url = reverse('delete_template_event', args=[self.template_event.id])

    def test_delete_template_event_as_authorized_coach(self):
        self.client.login(username='coachuser', password='testpass')
        response = self.client.post(self.url)

        # Confirm deletion
        self.assertEqual(TemplateEvent.objects.count(), 0)

        # Confirm redirection
        self.assertRedirects(response, reverse('schedule', args=[self.day.id]))

        # Confirm message
        messages = list(get_messages(response.wsgi_request))
        self.assertTrue(any("deleted successfully" in m.message.lower() for m in messages))

    def test_get_request_does_not_delete_template_event(self):
        self.client.login(username='coachuser', password='testpass')
        response = self.client.get(self.url)

        self.assertEqual(TemplateEvent.objects.count(), 1)
        self.assertRedirects(response, reverse('schedule', args=[self.day.id]))

    def test_unauthorized_user_cannot_delete_template_event(self):
        other_user = User.objects.create_user(username='randomuser', password='testpass')
        self.client.login(username='randomuser', password='testpass')

        response = self.client.post(self.url)

        # Should still exist
        self.assertEqual(TemplateEvent.objects.count(), 1)

        # Redirected to event search or error page
        self.assertRedirects(response, reverse('event_search', args=[date.today().isoformat()]))

        # Error message
        messages = list(get_messages(response.wsgi_request))
        self.assertTrue(any("not authorized" in m.message.lower() for m in messages))

# test for editing template events


class EditTemplateEventViewTest(TestCase):
    def setUp(self):
        # Create user and login
        self.user = User.objects.create_user(username='testuser', password='password')
        self.client.login(username='testuser', password='password')
        # Create company with user as manager
        self.company = Company.objects.create(name="TestCo", manager=self.user)
        # Create coach object
        self.coach = Coach.objects.create(coach=self.user, company=self.company)

        # Attach company to user profile (if applicable)
        self.user.profile.company = self.company
        self.user.profile.save()

        # Create venue under company
        self.venue = Venue.objects.create(name="Test Venue", company=self.company)

        # Create Day
        self.day = Day.objects.create(day="Monday")

        # Create TemplateEvent
        self.template = TemplateEvent.objects.create(
            event_name="Original Title",
            day_of_week=self.day,
            description='lorem',
            start_time=time(10, 0),
            end_time=time(11, 0),
            coach=self.coach,
            capacity=10,
            venue=self.venue,  # Assuming TemplateEvent has a venue field
        )

        # URL to edit the template event
        self.url = reverse('edit_template_event', args=[self.template.id])

    def test_get_edit_template_event_renders_form(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "booking/edit_template_event.html")
        self.assertIsInstance(response.context['form'], TemplateEventForm)
        self.assertContains(response, "Original Title")

    def test_post_valid_data_updates_template_event(self):
        post_data = {
            'event_name': 'Updated Title',
            'start_time': '12:00',
            'end_time': '13:00',
            'coach': self.coach.id,
            'day_of_week': self.day.id,
            'venue': self.venue.venue_id,
            'description': 'lorem',
            'capacity': 10,
        }
        response = self.client.post(self.url, data=post_data)
        self.template.refresh_from_db()
        self.assertEqual(self.template.event_name, 'Updated Title')
        self.assertRedirects(response, reverse('schedule', args=[self.day.id]))

    def test_post_invalid_data_shows_form_errors(self):
        post_data = {
            'event_name': '',  # Title required
            'start_time': '12:00',
            'end_time': '13:00',
            'coach': self.coach,
            'day_of_week': self.day.id,
            'venue': self.venue.venue_id,
        }
        response = self.client.post(self.url, data=post_data)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "booking/edit_template_event.html")
        self.assertFormError(response, 'form', 'event_name', 'This field is required.')

    def test_login_required_redirects_to_login(self):
        self.client.logout()
        response = self.client.get(self.url)
        self.assertRedirects(response, f"/accounts/login/?next={self.url}")

# tests for viewing template events



class ViewTemplateEventViewTest(TestCase):
    def setUp(self):
        # Create user and login
        self.user = User.objects.create_user(username='testuser', password='password')
        self.client.login(username='testuser', password='password')

        # Create company with user as manager
        self.company = Company.objects.create(name="TestCo", manager=self.user)

        # Create coach object
        self.coach = Coach.objects.create(coach=self.user, company=self.company)

        # Attach company to user profile if needed
        self.user.profile.company = self.company
        self.user.profile.save()

        # Create venue
        self.venue = Venue.objects.create(name="Test Venue", company=self.company)

        # Create day
        self.day = Day.objects.create(day="Monday")

        # Create TemplateEvent
        self.template = TemplateEvent.objects.create(
            event_name="Test Event",
            day_of_week=self.day,
            start_time="10:00",
            end_time="11:00",
            coach=self.coach,
            capacity=10,
            venue=self.venue,
        )

        self.url = reverse('view_template_event', args=[self.template.id])

    def test_authorized_coach_can_view_template_event(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'booking/view_template_event.html')

    def test_context_contains_template_event_and_is_coach_true(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertIn('template_event', response.context)
        self.assertEqual(response.context['template_event'], self.template)
        self.assertIn('is_coach', response.context)
        self.assertTrue(response.context['is_coach'])

    def test_view_template_event_unauthorized_user_redirects(self):
        # Logout current user and create a non-coach user
        self.client.logout()
        non_coach_user = User.objects.create_user(username='normaluser', password='password')
        self.client.login(username='normaluser', password='password')

        response = self.client.get(self.url, follow=True)
        self.assertRedirects(response, reverse('event_search', args=[date.today().isoformat()]))

        messages = list(get_messages(response.wsgi_request))
        self.assertTrue(any("not authorized" in str(m) for m in messages))

    def test_login_required_redirects_to_login(self):
        self.client.logout()
        response = self.client.get(self.url)
        login_url = reverse('account_login')
        self.assertRedirects(response, f"{login_url}?next={self.url}")

    def test_view_nonexistent_template_event_raises_404(self):
        # Use an ID that doesn't exist
        non_existent_id = 99999
        url = reverse('view_template_event', args=[non_existent_id])
        self.client.login(username='testuser', password='password')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 404)

    def test_view_template_event_invalid_template_id_type(self):
        self.client.login(username='testuser', password='password')
        # Hardcode the URL with a non-numeric ID
        url = '/booking/view_template_event/invalid_id/'
        response = self.client.get(url)
        self.assertEqual(response.status_code, 404)

    def test_view_template_event_when_user_has_no_profile(self):
        # Delete profile to simulate missing profile case (if your logic depends on profile)
        self.user.profile.delete()
        response = self.client.get(self.url)
        # If your code relies on profile existence, handle expected behavior here
        # For now, just check it still returns 200 or handles gracefully
        self.assertIn(response.status_code, [200, 302, 404])



class DuplicateTemplateScheduleViewTest(TestCase):
    def setUp(self):
        # Set up coach user
        self.coach_user = User.objects.create_user(username='coach', password='password')
        self.company = Company.objects.create(name="Test Company", manager=self.coach_user)
        self.coach = Coach.objects.create(coach=self.coach_user, company=self.company)
        self.coach_user.profile.save()
        self.venue = Venue.objects.create(
            name="Room 1",
            company=self.company,
            address="123 Main St",
            city="Testville",
            postcode="TE57GY",
        )

        self.another_venue = Venue.objects.create(
            name="Room 2",
            company=self.company,
            address="456 Another St",
            city="Testville",
            postcode="TE58GY",
        )

        # Non-coach user
        self.normal_user = User.objects.create_user(username='user', password='password')

        # Days
        self.source_day = Day.objects.create(day="Monday")
        self.target_day = Day.objects.create(day="Tuesday")

        # Source template events
        self.template_event = TemplateEvent.objects.create(
            coach=self.coach,
            day_of_week=self.source_day,
            event_name="Yoga",
            description="Morning session",
            venue=self.venue,
            start_time=time(9, 0),
            end_time=time(10, 0),
            capacity=10,
        )

        self.url = reverse('duplicate_template_schedule', args=[self.source_day.id])

    def test_login_required(self):
        """Test that the view requires login."""
        response = self.client.get(self.url)
        login_url = reverse('account_login')
        self.assertRedirects(response, f"{login_url}?next={self.url}")

    def test_non_coach_user_redirects(self):
        """Test that a non-coach user is redirected."""
        self.client.login(username='user', password='password')
        response = self.client.get(self.url, follow=True)
        self.assertRedirects(response, reverse('event_search', args=[date.today().isoformat()]))
        messages = list(get_messages(response.wsgi_request))
        self.assertTrue(any("not authorized" in str(m) for m in messages))

    def test_get_request_displays_form(self):
        """Test that a GET request displays the duplication form."""
        self.client.login(username='coach', password='password')
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'booking/duplicate_template_schedule.html')
        self.assertIn('form', response.context)
        self.assertIn('source_day', response.context)
        self.assertEqual(response.context['source_day'], self.source_day)

    def test_successful_post_duplicates_events(self):
        """Test that a valid POST request duplicates events."""
        self.client.login(username='coach', password='password')
        response = self.client.post(self.url, {
            'target_day': self.target_day.id
        }, follow=True)

        self.assertRedirects(response, reverse('schedule', args=[self.target_day.id]))
        messages = list(get_messages(response.wsgi_request))
        self.assertTrue(any("Successfully duplicated" in str(m) for m in messages))

        duplicated_events = TemplateEvent.objects.filter(day_of_week=self.target_day)
        self.assertEqual(duplicated_events.count(), 1)
        self.assertEqual(duplicated_events.first().event_name, "Yoga")

    def test_existing_target_day_events_are_cleared(self):
        """Test that existing events on the target day are cleared before duplication."""
        # Add an event to the target day
        TemplateEvent.objects.create(
            coach=self.coach,
            day_of_week=self.target_day,
            event_name="Spin Class",
            description="Evening",
            venue=self.another_venue,
            start_time=time(18, 0),
            end_time=time(19, 0),
            capacity=15,
        )

        self.client.login(username='coach', password='password')
        self.client.post(self.url, {
            'target_day': self.target_day.id
        })

        # The original event should be deleted
        remaining_events = TemplateEvent.objects.filter(day_of_week=self.target_day)
        self.assertEqual(remaining_events.count(), 1)
        self.assertEqual(remaining_events.first().event_name, "Yoga")

    def test_invalid_form_shows_form_again(self):
        """Test that an invalid form submission shows the form with errors."""
        self.client.login(username='coach', password='password')
        response = self.client.post(self.url, {
            'target_day': ''  # Invalid
        })
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'booking/duplicate_template_schedule.html')
        self.assertFormError(response, 'form', 'target_day', 'This field is required.')

    def test_source_and_target_days_cannot_be_same(self):
        """Test that source and target days cannot be the same."""
        self.client.login(username='coach', password='password')
        response = self.client.post(self.url, {
            'target_day': self.source_day.id  # Same as source day
        }, follow=True)

        self.assertRedirects(response, reverse('schedule', args=[self.source_day.id]))
        messages = list(get_messages(response.wsgi_request))
        self.assertTrue(any("Source and target days cannot be the same" in str(m) for m in messages))