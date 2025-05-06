from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User
from logbook.models import Exercise, Score
from logbook.forms import ScoreForm


# Test the Logbook views
class LogbookViewsTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username='testuser',
                                             password='testpass')
        self.exercise = Exercise.objects.create(name='Test Exercise')
        self.score = Score.objects.create(user=self.user,
                                          exercise=self.exercise,
                                          reps=10, weight=50.0)

    # Test that the logbook view is displayed when the user is authenticated
    def test_logbook_view_authenticated(self):
        self.client.login(username='testuser', password='testpass')
        response = self.client.get(reverse('open_log'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'logbook/logbook.html')
        self.assertContains(response, 'Logbook')
        self.assertContains(response, 'New Score')
        self.assertContains(response, 'Recent Scores')

    # Test that the logbook view is displayed when the user isnt authenticated
    def test_logbook_view_unauthenticated(self):
        response = self.client.get(reverse('open_log'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'logbook/logbook.html')
        self.assertContains(response, 'Welcome to the ClassFit Logbook')
        self.assertContains(response, 'Sign up or log in to get started.')

    # Test that the add score view is displayed when the user is authenticated
    def test_add_score_authenticated(self):
        self.client.login(username='testuser', password='testpass')
        form_data = {
            'exercise': self.exercise.id,
            'reps': 15,
            'weight': 60.0,
        }
        response = self.client.post(reverse('open_log'), data=form_data)
        self.assertEqual(response.status_code, 302)
        self.assertTrue(Score.objects.filter(reps=15, weight=60.0).exists())

    # Test that the add score view isnt displayed if a user isnt authenticated
    def test_add_score_unauthenticated(self):
        form_data = {
            'exercise': self.exercise.id,
            'reps': 15,
            'weight': 60.0,
        }
        response = self.client.post(reverse('open_log'), data=form_data)
        self.assertEqual(response.status_code, 200)
        self.assertFalse(Score.objects.filter(reps=15, weight=60.0).exists())

    # Test that the edit score view is displayed when the user is authenticated
    def test_edit_score_view(self):
        self.client.login(username='testuser', password='testpass')
        form_data = {
            'exercise': self.exercise.id,
            'reps': 20,
            'weight': 70.0,
        }
        response = self.client.post(reverse('edit_score',
                                            args=[self.score.id]),
                                    data=form_data)
        self.assertEqual(response.status_code, 302)
        self.score.refresh_from_db()
        self.assertEqual(self.score.reps, 20)
        self.assertEqual(self.score.weight, 70.0)

    # Test that the edit score view isnt displayed when user not authenticated
    def test_delete_score_view(self):
        self.client.login(username='testuser', password='testpass')
        response = self.client.post(reverse('delete_score',
                                    args=[self.score.id]))
        self.assertEqual(response.status_code, 302)
        self.assertFalse(Score.objects.filter(id=self.score.id).exists())
