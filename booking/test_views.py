from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User
from .models import Event, Booking, Coach
from .forms import EventForm
from datetime import datetime, timedelta


class BookingViewsTest(TestCase):
    def setUp(self):
        # Set up the test client
        self.client = Client()
        # Create a test user
        self.user = User.objects.create_user(username='testuser',
                                             password='testpass')
        # Create a coach associated with the test user
        self.coach = Coach.objects.create(coach=self.user)
        # Create a test event
        self.event = Event.objects.create(
            coach=self.coach,
            event_name='Test Event',
            description='This is a test event.',
            date_of_event='2023-12-31',
            capacity=10,
            start_time='10:00',
            end_time='12:00',
            status=0,
        )

    def test_event_detail_view(self):
        # Log in the test user
        self.client.login(username='testuser', password='testpass')
        # Send a GET request to the 'event_detail' view
        response = self.client.get(reverse('event_detail',
                                           args=[self.event.date_of_event,
                                                 self.event.id]))
        # Check if the response status code is 200 (OK)
        self.assertEqual(response.status_code, 200)
        # Check if the correct template is used
        self.assertTemplateUsed(response, 'booking/event_detail.html')

    def test_event_search_view(self):
        # Log in the test user
        self.client.login(username='testuser', password='testpass')
        # Send a GET request to the 'event_search' view
        response = self.client.get(reverse('event_search',
                                           args=['2023-12-31']))
        # Check if the response status code is 200 (OK)
        self.assertEqual(response.status_code, 200)
        # Check if the correct template is used
        self.assertTemplateUsed(response, 'booking/index.html')

    def test_book_event_view(self):
        # Log in the test user
        self.client.login(username='testuser', password='testpass')
        # Send a POST request to the 'book_event' view
        response = self.client.post(reverse('book_event',
                                            args=[self.event.id]))
        # Check if the response status code is 302 (redirection)
        self.assertEqual(response.status_code, 302)
        # Check if the booking was created successfully
        self.assertTrue(Booking.objects.filter(event=self.event,
                                               user=self.user).exists())

    def test_cancel_event_view(self):
        # Log in the test user
        self.client.login(username='testuser', password='testpass')
        # Create a booking for the event
        booking = Booking.objects.create(event=self.event, user=self.user)
        # Send a POST request to the 'cancel_event' view
        response = self.client.post(reverse('cancel_event',
                                    args=[self.event.id]))
        # Check if the response status code is 302 (redirection)
        self.assertEqual(response.status_code, 302)
        # Check if the booking was cancelled successfully
        self.assertFalse(Booking.objects.filter(event=self.event,
                                                user=self.user).exists())

    def test_delete_event_view(self):
        # Log in the test user
        self.client.login(username='testuser', password='testpass')
        # Send a POST request to the 'delete_event' view
        response = self.client.post(reverse('delete_event',
                                            args=[self.event.id]))
        # Check if the response status code is 302 (redirection)
        self.assertEqual(response.status_code, 302)
        # Check if the event was deleted successfully
        self.assertFalse(Event.objects.filter(id=self.event.id).exists())

    def test_create_event_view(self):
        # Log in the test user
        self.client.login(username='testuser', password='testpass')
        # Define form data for creating a new event
        form_data = {
            'coach': self.coach.id,
            'event_name': 'New Event',
            'description': 'This is a new event.',
            'date_of_event': '2023-12-31',
            'capacity': 10,
            'start_time': '14:00',
            'end_time': '16:00',
            'status': 0,
        }

        # Send a POST request to the 'create_event' view with the form data
        response = self.client.post(reverse('create_event'), data=form_data)
        # Check if the response status code is 302 (redirection)
        self.assertEqual(response.status_code, 302,
                         msg=f"Response content: {response.content}")
        # Check if the event was created successfully
        self.assertTrue(Event.objects.filter(event_name='New Event').exists())

    def test_edit_event_view(self):
        # Log in the test user
        self.client.login(username='testuser', password='testpass')
        # Define form data for editing the event
        form_data = {
            'coach': self.coach.id,
            'event_name': 'Updated Event',
            'description': 'This is an updated event.',
            'date_of_event': '2023-12-31',
            'capacity': 15,
            'start_time': '10:00',
            'end_time': '12:00',
            'status': 0,
        }

        # Send a POST request to the 'edit_event' view with the form data
        response = self.client.post(reverse('edit_event',
                                    args=[self.event.id]), data=form_data)
        # Check if the response status code is 302 (redirection)
        self.assertEqual(response.status_code, 302,
                         msg=f"Response content: {response.content}")
        # Refresh the event instance from the database
        self.event.refresh_from_db()
        # Verify that the event name has been updated correctly
        self.assertEqual(self.event.event_name, 'Updated Event',
                         msg=f"Event name: {self.event.event_name}")
        # Verify that the event capacity has been updated correctly
        self.assertEqual(self.event.capacity, 15,
                         msg=f"Event capacity: {self.event.capacity}")
