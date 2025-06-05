from django.shortcuts import render, get_object_or_404, redirect
from django.http import HttpResponse
from .models import Event, Booking, Coach
from django.views import generic
from datetime import timedelta, datetime
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from .forms import EventForm, MultiEventForm
from datetime import date, timedelta
from django.shortcuts import render, redirect
from company.models import Token

import logging

logger = logging.getLogger(__name__)


def check_for_coach(request):
    coaches = Coach.objects.all()
    for coach in coaches:
        if request.user == coach.coach:
            return True
    return False


@login_required
def event_detail(request, id, date):
    current_date = datetime.strptime(date, "%Y-%m-%d").date()
    queryset = Event.objects.filter(status=0, date_of_event=current_date)
    event = get_object_or_404(queryset, id=id, date_of_event=current_date)

    return render(
        request,
        "booking/event_detail.html",
        {"event": event,
         'is_coach': check_for_coach(request)}
    )


@login_required
def get_events_for_date(date):
    return Event.objects.filter(date_of_event=date).order_by('start_time')


@login_required
def event_search(request, date):
    try:
        current_date = datetime.strptime(date, "%Y-%m-%d").date()
    except ValueError:
        return HttpResponse("Invalid date format", status=400)

    previous_date = current_date - timedelta(days=1)
    next_date = current_date + timedelta(days=1)

    user_company = request.user.profile.company
    events = Event.objects.filter(coach__company=user_company, date_of_event=current_date, status=0)
    events = events.order_by('start_time')
    for event in events:
        event.is_user_booked = event.is_user_booked(request.user)

    is_coach = check_for_coach(request)
    tokens = Token.objects.filter(user=request.user, used=False, company=user_company).count()

    return render(request, "booking/index.html", {
        "events": events,
        "current_date": current_date,
        "previous_date": previous_date,
        "next_date": next_date,
        'is_coach': is_coach,
        'tokens': tokens,
    })


# used to create a booking with tokens

def book_event(request, event_id):
    event = get_object_or_404(Event, pk=event_id)

    if request.method == 'POST':
        # Check if event is full
        if event.is_full():
            messages.error(request, "Event is full")
            return redirect('event_search', date=event.date_of_event)

        # Check if user has already booked
        if event.is_user_booked(request.user):
            messages.error(request, "You have already booked this event")
            return redirect('event_search', date=event.date_of_event)

        # Check for available token
        token = Token.objects.filter(user=request.user, used=False).first()
        if not token:
            messages.error(request, "You don't have any available tokens to book this class.")
            return redirect('event_search', date=event.date_of_event)

        # Mark token as used
        token.used = True
        token.save()

        # Proceed with booking
        Booking.objects.create(event=event, user=request.user)
        messages.success(request, "Event booked successfully. 1 token has been used.")
        return redirect('event_search', date=event.date_of_event)

    return redirect('event_search', date=event.date_of_event)



# used to cancel a booking
def cancel_event(request, event_id):
    user = request.user
    event = get_object_or_404(Event, pk=event_id)
    if request.method == 'POST':
        booking = Booking.objects.filter(event=event, user=user).first()
        if booking:
            booking.delete()
            messages.success(request, "Booking cancelled successfully")
        else:
            messages.error(request, "You do not have a booking for this event")
        return redirect('event_search', date=event.date_of_event)
    return redirect('event_search', date=event.date_of_event)


# The coach views

def delete_event(request, event_id):
    event = get_object_or_404(Event, pk=event_id)
    if request.method == 'POST':
        event.delete()
        messages.success(request, "Event deleted successfully")
        return redirect('event_search', date=event.date_of_event)
    return redirect('event_search', date=event.date_of_event)


@login_required
def create_event(request):
    # Check if the user is a coach
    try:
        coach = Coach.objects.get(coach=request.user)  # <-- FIXED HERE
    except Coach.DoesNotExist:
        messages.error(request, "You are not authorized to create events")
        return redirect('event_search', date=date.today())

    if request.method == 'POST':
        form = EventForm(request.POST, user=request.user, request=request)
        if form.is_valid():
            event = form.save(commit=False)
            event.coach = coach  # Reuse the coach object you already got
            event.save()
            messages.success(request, "Event created successfully")
            return redirect('event_search', date=event.date_of_event)
        else:
            print(form.errors)
    else:
        form = EventForm(user=request.user, request=request)
    return render(request, "booking/create_event.html", {'form': form})


@login_required
def create_multi_event(request):
    if request.method == 'POST':
        form = MultiEventForm(request.POST, user=request.user)
        if form.is_valid():
            date_input = form.cleaned_data['date_of_event']
            coach_input = Coach.objects.get(coach=request.user)
            venue_input = form.cleaned_data['venue']  # Get the venue from the form
            start_time = form.cleaned_data['start_time']
            end_time = form.cleaned_data['end_time']
            frequency_input = form.cleaned_data['frequency']
            gap_input = form.cleaned_data['gap']
            event_name = form.cleaned_data['event_name']
            description = form.cleaned_data['description']
            capacity = form.cleaned_data['capacity']
            status = form.cleaned_data['status']

            events_to_create = []

            # Create the first event
            first_event = Event(
                coach=coach_input,
                event_name=event_name,
                description=description,
                date_of_event=date_input,
                venue=venue_input,  # Set the venue
                capacity=capacity,
                start_time=start_time,
                end_time=end_time,
                status=status,
            )
            events_to_create.append(first_event)

            # Handle repetition logic
            if frequency_input > 1:
                current_start_datetime = datetime.combine(date_input, end_time)
                duration_timedelta = datetime.combine(date_input, end_time) - datetime.combine(date_input, start_time)

                for _ in range(frequency_input - 1):
                    current_start_datetime += timedelta(minutes=gap_input)
                    next_end_datetime = current_start_datetime + duration_timedelta

                    if current_start_datetime.date() == date_input:
                        repeated_event = Event(
                            coach=coach_input,
                            event_name=event_name,
                            description=description,
                            date_of_event=date_input,
                            venue=venue_input,  # Set the venue
                            capacity=capacity,
                            start_time=current_start_datetime.time(),
                            end_time=next_end_datetime.time(),
                            status=status,
                        )
                        events_to_create.append(repeated_event)
                    else:
                        break

            # Bulk create all events
            Event.objects.bulk_create(events_to_create)
            messages.success(request, "Events created successfully")
            return redirect('event_search', date=date_input)
        else:
            messages.error(request, 'Form is invalid. Please correct the errors.')
            return render(request, 'booking/multi_event.html', {'form': form})
    else:
        form = MultiEventForm(user=request.user)
    return render(request, 'booking/multi_event.html', {'form': form})


@login_required
def duplicate_event(request, date_str):
    # Parse the date string into a `date` object
    try:
        selected_date = datetime.strptime(date_str, "%Y-%m-%d").date()
    except ValueError:
        return HttpResponse("Invalid date format", status=400)
    
    coach_input = get_object_or_404(Coach, coach=request.user)

    if request.method == 'POST':
        # Get the events for the selected date
        events = Event.objects.filter(date_of_event=selected_date, coach__company=coach_input.company)

        # Create a list to hold the new events
        new_events = []

        date_input = request.POST.get('dates-sent')
        # Check if the date input is valid
        if date_input:
            date_array = [date.strip() for date in date_input.split(',')]
        else:
            messages.error(request, "Invalid date input")
            return redirect('event_search', date=selected_date)

        # Loop through each event and create a new one
        for event in events:
            for day in date_array:
                if event.coach.company == coach_input.company and event.coach == coach_input:
                    new_event = Event(
                        coach=event.coach,
                        event_name=event.event_name,
                        description=event.description,
                        venue = event.venue,
                        date_of_event= day,
                        capacity=event.capacity,
                        start_time=event.start_time,
                        end_time=event.end_time,
                        status=event.status,
                    )
                    new_events.append(new_event)

        # Bulk create the new events
        Event.objects.bulk_create(new_events)
        messages.success(request, "Events duplicated successfully")
        return redirect('event_search', date=selected_date)
    else:
        return render(request, 'booking/duplicate_events.html', {'selected_date': selected_date})


@login_required
def edit_event(request, event_id):
    event = get_object_or_404(Event, pk=event_id)
    if request.method == 'POST':
        form = EventForm(request.POST, instance=event)
        if form.is_valid():
            event = form.save()
            messages.success(request, "Event updated successfully")
            return redirect('event_search', date=event.date_of_event)
        else:
            print(form.errors)  # Debugging information
    else:
        form = EventForm(instance=event)
    return render(
        request,
        "booking/edit_event.html",
        {"event": event,
         'form': form}
    )


