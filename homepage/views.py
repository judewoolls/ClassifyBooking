from django.shortcuts import render
from booking.models import Booking
from logbook.models import Score, Exercise
from django.contrib.auth.models import User
from .forms import LeaderboardFilterForm
from django.utils import timezone
from django.contrib.auth.decorators import login_required


# Home page view
@login_required
def home(request):
    # Get the current user
    user = request.user
    if user.is_authenticated:

        # Query bookings made by the user and order by the date of the event
        current_date = timezone.now().date()
        bookings = Booking.objects.filter(user=user)
        # filter to only include future events
        bookings = bookings.filter(event__date_of_event__gte=current_date)
        bookings = bookings.order_by('event__date_of_event')
        # Query scores made by the user
        scores = Score.objects.filter(user=user).order_by('-created_on')

        if request.method == 'GET':
            leaderboard_filter = LeaderboardFilterForm(request.GET)
            if leaderboard_filter.is_valid():
                exercise = leaderboard_filter.cleaned_data.get('exercise')
                min_reps = leaderboard_filter.cleaned_data.get('min_reps')
                min_weight = leaderboard_filter.cleaned_data.get('min_weight')

                leaderboard = Score.objects.all()
                if exercise:
                    leaderboard = leaderboard.filter(exercise=exercise)
                if min_reps:
                    leaderboard = leaderboard.filter(reps__gte=min_reps)
                if min_weight:
                    leaderboard = leaderboard.filter(weight__gte=min_weight)
            else:
                leaderboard = Score.objects.all()
        else:
            leaderboard_filter = LeaderboardFilterForm()
            leaderboard = Score.objects.all()

        return render(request, 'homepage/home.html', {
            'exercises': Exercise.objects.all(),
            'bookings': bookings,
            'scores': scores,
            'filter': leaderboard_filter,
            'leaderboard': leaderboard.order_by('-weight', '-reps'),
        })
    else:
        return render(request, 'homepage/home.html')
