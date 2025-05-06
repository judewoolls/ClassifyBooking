from django.shortcuts import render, get_object_or_404, redirect
from django.http import HttpResponse
from .models import Event, Booking, Coach
from django.views import generic
from datetime import timedelta, datetime
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from .forms import EventForm, MultiEventForm

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

    events = Event.objects.filter(date_of_event=current_date, status=0)
    events = events.order_by('start_time')
    for event in events:
        event.is_user_booked = event.is_user_booked(request.user)

    is_coach = check_for_coach(request)

    return render(request, "booking/index.html", {
        "events": events,
        "current_date": current_date,
        "previous_date": previous_date,
        "next_date": next_date,
        'is_coach': is_coach,
    })


# used to create a booking
def book_event(request, event_id):
    event = get_object_or_404(Event, pk=event_id)
    if request.method == 'POST':
        if event.is_full():
            messages.error(request, "Event is full")
            return redirect('event_search', date=event.date_of_event)

        if event.is_user_booked(request.user):
            messages.error(request, "You have already booked this event")
            return redirect('event_search', date=event.date_of_event)

        booking = Booking(event=event, user=request.user)
        booking.save()
        messages.success(request, "Event booked successfully")
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
    if request.method == 'POST':
        form = EventForm(request.POST)
        if form.is_valid():
            event = form.save(commit=False)
            event.coach = Coach.objects.get(coach=request.user)
            event.save()
            messages.success(request, "Event created successfully")
            return redirect('event_search', date=event.date_of_event)
        else:
            print(form.errors)  # Debugging information
    else:
        form = EventForm()
    return render(
        request,
        "booking/create_event.html",
        {"coaches": Coach.objects.filter(coach=request.user),
         'form': form}
    )


@login_required
def create_multi_event(request):
    if request.method == 'POST':
        form = MultiEventForm(request.POST)
        if form.is_valid():
            date_input = form.cleaned_data['date_of_event']
            coach_input = Coach.objects.get(coach=request.user)
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
                capacity=capacity,
                start_time=start_time,
                end_time=end_time,
                status=status,
            )
            events_to_create.append(first_event)

            # Handle repetition logic
            if frequency_input > 1:  # Changed to > 1
                current_start_datetime = datetime.combine(date_input, end_time)
                duration_timedelta = datetime.combine(date_input, end_time) - datetime.combine(date_input, start_time)

                for _ in range(frequency_input - 1): # Changed to frequency_input -1
                    current_start_datetime += timedelta(minutes=gap_input)
                    next_end_datetime = current_start_datetime + duration_timedelta

                    # Check if the next event's start time is still on the same day
                    if current_start_datetime.date() == date_input:
                        repeated_event = Event(
                            coach=coach_input,
                            event_name=event_name,
                            description=description,
                            date_of_event=date_input,
                            capacity=capacity,
                            start_time=current_start_datetime.time(),
                            end_time=next_end_datetime.time(),
                            status=status,
                        )
                        events_to_create.append(repeated_event)
                    else:
                        break  # Stop adding events

            # Bulk create all events
            Event.objects.bulk_create(events_to_create)
            messages.success(request, "Events created successfully")
            return redirect('event_search', date=date_input)
        else:
            logger.warning(f"Form is invalid. Errors: {form.errors}")
            print(form.errors)
            return render(request, 'booking/multi_event.html', {'form': form})
    else:
        form = MultiEventForm()
    return render(
        request,
        "booking/multi_event.html",
        {"form": form}
    )



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
