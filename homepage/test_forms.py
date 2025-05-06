from django.test import TestCase
from logbook.models import Exercise
from homepage.forms import LeaderboardFilterForm


class LeaderboardFilterFormTest(TestCase):
    def setUp(self):
        self.exercise = Exercise.objects.create(name='Test Exercise')

    # Test that the form is valid when the data is valid
    def test_leaderboard_filter_form_valid(self):
        form_data = {
            'exercise': self.exercise.id,
            'min_reps': 10,
            'min_weight': 50.0,
        }
        form = LeaderboardFilterForm(data=form_data)
        self.assertTrue(form.is_valid())

    # Test that the form is valid when the data is missing
    def test_leaderboard_filter_form_valid_missing_fields(self):
        form_data = {
            'exercise': self.exercise.id,
            'min_reps': '',
            'min_weight': '',
        }
        form = LeaderboardFilterForm(data=form_data)
        self.assertTrue(form.is_valid())

    # Test that the form is invalid when the data is invalid
    def test_leaderboard_filter_form_invalid(self):
        form_data = {
            'exercise': '',  # Invalid exercise
            'min_reps': -1,  # Invalid min_reps
            'min_weight': -10.0,  # Invalid min_weight
        }
        form = LeaderboardFilterForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('min_reps', form.errors)
        self.assertIn('min_weight', form.errors)
