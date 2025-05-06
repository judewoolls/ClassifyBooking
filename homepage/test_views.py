from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User
from booking.models import Booking, Event, Coach
from logbook.models import Score, Exercise
from datetime import datetime, timedelta


class HomepageViewsTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username='testuser',
                                             password='testpass')
        self.coach = Coach.objects.create(coach=self.user)
        self.exercise = Exercise.objects.create(name='Test Exercise')
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
        self.booking = Booking.objects.create(event=self.event, user=self.user)
        self.score = Score.objects.create(user=self.user,
                                          exercise=self.exercise,
                                          reps=10, weight=50.0)

    # checks if user is authenticated
    def test_home_view_authenticated(self):
        self.client.login(username='testuser', password='testpass')
        response = self.client.get(reverse('home'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'homepage/home.html')
        self.assertContains(response, 'Welcome to ClassFit')
        self.assertContains(response, 'Your Upcoming Bookings')
        self.assertContains(response, 'Your Recent Scores')

    # checks if user is not authenticated
    def test_home_view_unauthenticated(self):
        response = self.client.get(reverse('home'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'homepage/home.html')
        self.assertContains(response, 'Welcome to ClassFit')
        self.assertContains(response, 'Sign up or log in to get started.')

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
