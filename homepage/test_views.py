from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User
from booking.models import Booking, Event, Coach
from logbook.models import Score, Exercise
from datetime import datetime, timedelta

from company.models import Company, Venue

class HomepageViewsTest(TestCase):
    def setUp(self):
        self.client = Client()

        # Create a user
        self.user = User.objects.create_user(username='testuser', password='testpass')

        # Create a company and associate it with the coach
        self.company = Company.objects.create(name="Test Company", manager=self.user)
        self.coach = Coach.objects.create(coach=self.user, company=self.company)

        # Create a venue
        self.venue = Venue.objects.create(name="Main Hall", company=self.company)

        # Create an exercise
        self.exercise = Exercise.objects.create(name='Test Exercise')
        self.user.profile.company = self.company
        self.user.profile.save()

        # Create an event associated with the coach, company, and venue
        self.event = Event.objects.create(
            coach=self.coach,
            event_name='Test Event',
            description='This is a test event.',
            date_of_event='2023-12-31',
            capacity=10,
            start_time='10:00',
            end_time='12:00',
            status=0,
            venue=self.venue,  # Associate the event with the venue
        )

        # Create a booking for the event
        self.booking = Booking.objects.create(event=self.event, user=self.user)

        # Create a score for the exercise
        self.score = Score.objects.create(user=self.user, exercise=self.exercise, reps=10, weight=50.0)

    # checks if user is authenticated
    def test_home_view_authenticated(self):
        self.client.login(username='testuser', password='testpass')
        response = self.client.get(reverse('home'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'homepage/home.html')
        self.assertContains(response, 'Welcome to ClassifyBooking')  # Update to match actual text
        self.assertContains(response, 'Your Upcoming Bookings')
        self.assertContains(response, 'Your Recent Scores')

    # checks if user is not authenticated
    def test_home_view_unauthenticated(self):
        response = self.client.get(reverse('home'))
        login_url = reverse('account_login')  # Get the login URL dynamically
        self.assertRedirects(response, f"{login_url}?next={reverse('home')}", status_code=302, target_status_code=200)

    # checks if leaderboard is displayed
    def test_home_view_leaderboard_filter(self):
        self.client.login(username='testuser', password='testpass')
        form_data = {
            'exercise': self.exercise.id,
            'min_reps': 5,
            'min_weight': 20.0,
        }
        response = self.client.get(reverse('home'), data=form_data)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'homepage/home.html')
        self.assertContains(response, 'Our Leaderboard')
        self.assertContains(response, 'Test Exercise')
        self.assertContains(response, '10 reps @ 50.0kg')

    # checks if no bookings or scores are displayed
    def test_home_view_no_bookings(self):
        self.client.login(username='testuser', password='testpass')
        Booking.objects.all().delete()
        response = self.client.get(reverse('home'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'homepage/home.html')
        self.assertContains(response, 'No Upcoming Bookings')

    # checks if no scores are displayed
    def test_home_view_no_scores(self):
        self.client.login(username='testuser', password='testpass')
        Score.objects.all().delete()
        response = self.client.get(reverse('home'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'homepage/home.html')
        self.assertContains(response, 'No Recent Scores')
