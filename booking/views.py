from django.shortcuts import render, get_object_or_404, redirect
from django.http import HttpResponse
from .models import Event, Booking, Coach, TemplateEvent, ExcludedDate, Day
from django.views import generic
from datetime import timedelta, datetime
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from .forms import EventForm, MultiEventForm, TemplateEventForm, DuplicateTemplateDayForm, BulkDeleteEventsForm
from datetime import date, timedelta
from django.shortcuts import render, redirect
from company.models import Token
from booking.utils import update_event_status_if_needed, generate_schedule_for_next_30_days

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
    queryset = Event.objects.filter(date_of_event=current_date)
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
    events = Event.objects.filter(coach__company=user_company, date_of_event=current_date)
    events = events.order_by('start_time')
    for event in events:
        update_event_status_if_needed(event) # check to see if each event has started
        event.is_user_booked = event.is_user_booked(request.user) # checks if user is booked

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
@login_required
def book_event(request, event_id):
    event = get_object_or_404(Event, pk=event_id)

    update_event_status_if_needed(event)

    if event.status == 1:  # Past event
        messages.error(request, "You can't book after the class has started.")
        return redirect('event_search', date=event.date_of_event)

    if request.method == 'POST':
        # Check if event is full
        if event.is_full():
            messages.error(request, "Event is full")
            return redirect('event_search', date=event.date_of_event)

        # Check if user has already booked
        if event.is_user_booked(request.user):
            messages.error(request, "You have already booked this event")
            return redirect('event_search', date=event.date_of_event)

        # Check for overlapping events
        overlapping_events = Booking.objects.filter(
            user=request.user,
            event__date_of_event=event.date_of_event,
            event__start_time__lt=event.end_time,
            event__end_time__gt=event.start_time
        )
        if overlapping_events.exists():
            messages.error(request, "You cannot book overlapping events")
            return redirect('event_search', date=event.date_of_event)

        # Check for available token
        token = Token.objects.filter(user=request.user, used=False, company=event.coach.company).first()
        if not token:
            messages.error(request, "You don't have any available tokens")
            return redirect('event_search', date=event.date_of_event)
        

        # Proceed with booking
        Booking.objects.create(event=event, user=request.user)
        token.used = True
        token.booking = Booking.objects.filter(event=event, user=request.user).first()
        token.save()

        messages.success(request, "Event booked successfully. 1 token has been used.")
        return redirect('event_search', date=event.date_of_event)

    return redirect('event_search', date=event.date_of_event)



# used to cancel a booking
@login_required
def cancel_event(request, event_id):
    user = request.user
    event = get_object_or_404(Event, pk=event_id)

    update_event_status_if_needed(event)

    if event.status == 1:  # Past event
        messages.error(request, "You can't cancel a booking after the class has started.")
        return redirect('event_search', date=event.date_of_event)

    if request.method == 'POST':
        booking = Booking.objects.filter(event=event, user=user).first()
        if booking:
            # Find and refund the token linked to this booking
            token = Token.objects.filter(user=user, booking=booking, used=True).first()
            if token:
                token.used = False
                token.booking = None
                token.save()
            else:
                messages.error(request, "No token found for this booking to refund.")
            booking.delete()
            messages.success(request, "Booking cancelled successfully and token refunded.")
        else:
            messages.error(request, "You do not have a booking for this event")
        return redirect('event_search', date=event.date_of_event)
    return redirect('event_search', date=event.date_of_event)


# The coach views
@login_required
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
        form = EventForm(user=request.user, request=request)
    return render(request, "booking/create_event.html", {'form': form})



@login_required
def create_multi_event(request):
    try:
        coach = Coach.objects.get(coach=request.user)
    except Coach.DoesNotExist:
        messages.error(request, "You do not have permission to create events.")
        return redirect('event_search', date=date.today())

    if request.method == "POST":
        form = MultiEventForm(request.POST, user=request.user)
        if form.is_valid():
            date_ = form.cleaned_data["date_of_event"]
            venue = form.cleaned_data["venue"]
            start_time = form.cleaned_data["start_time"]
            end_time = form.cleaned_data["end_time"]
            repeat = form.cleaned_data["frequency"]
            gap_minutes = form.cleaned_data["gap"]
            name = form.cleaned_data["event_name"]
            desc = form.cleaned_data["description"]
            cap = form.cleaned_data["capacity"]
            status = form.cleaned_data["status"]

            events = []
            gap_td = timedelta(minutes=gap_minutes)
            dur_td = datetime.combine(date_, end_time) - datetime.combine(date_, start_time)

            start_dt = datetime.combine(date_, start_time)

            for _ in range(repeat):
                end_dt = start_dt + dur_td

                # Break if start or end spills into the next day
                if start_dt.date() != date_:
                    break

                events.append(
                    Event(
                        coach=coach,
                        venue=venue,
                        event_name=name,
                        description=desc,
                        date_of_event=date_,
                        capacity=cap,
                        start_time=start_dt.time(),
                        end_time=end_dt.time(),
                        status=status,
                    )
                )

                # Next class
                start_dt = end_dt + gap_td

            if events:
                Event.objects.bulk_create(events)
                messages.success(request, f"{len(events)} event(s) created successfully.")
                return redirect("event_search", date=date_)
            else:
                messages.error(request, "No events were created. Please check your input.")
                return render(request, "booking/multi_event.html", {"form": form})

        messages.error(request, "Form is invalid. Please correct the errors.")
        return render(request, "booking/multi_event.html", {"form": form})

    form = MultiEventForm(user=request.user)
    return render(request, "booking/multi_event.html", {"form": form})


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
        form = EventForm(request.POST, instance=event, user=request.user)
        if form.is_valid():
            event = form.save()
            messages.success(request, "Event updated successfully")
            return redirect('event_search', date=event.date_of_event)

    else:
        form = EventForm(instance=event, user=request.user)
    return render(
        request,
        "booking/edit_event.html",
        {"event": event,
         'form': form}
    )

@login_required
def coach_dashboard(request):
    if not check_for_coach(request):
        messages.error(request, "You are not authorized to view this page")
        return redirect('event_search', date=date.today())

    coach = get_object_or_404(Coach, coach=request.user)
    company = coach.company

    return render(
        request,
        "booking/coach_dashboard.html",
        {'is_coach': True, 'company': company}
    )

@login_required
def schedule(request, day_id):
    if not check_for_coach(request):
        messages.error(request, "You are not authorized to view this page")
        return redirect('event_search', date=date.today())

    day = get_object_or_404(Day, id=day_id)
    # Ensure the user is a coach
    coach = get_object_or_404(Coach, coach=request.user)
    template_events = TemplateEvent.objects.filter(coach=coach, day_of_week=day).order_by('start_time')

    return render(
        request,
        "booking/schedule.html",
        {'template_events': template_events, 'is_coach': True, 'day': day}
    )


@login_required
def add_template_event(request, day_id):
    day = get_object_or_404(Day, id=day_id)

    if request.method == 'POST':
        form = TemplateEventForm(request.POST, user=request.user, day_id=day.id)
        if form.is_valid():
            form.save()
            messages.success(request, 'Template event created successfully.')
            return redirect('schedule', day_id=day.id) 
        else:
            messages.error(request, 'There was a problem with the form. Please try again.')
    else:
        form = TemplateEventForm(user=request.user, day_id=day.id)

    return render(
        request,
        'booking/template_event.html',
        {'is_coach': True, 'form': form, 'day_id': day_id, 'day': day}
    )

@login_required
def delete_template_event(request, template_id):
    template = get_object_or_404(TemplateEvent, pk=template_id)
    day = get_object_or_404(Day, id=template.day_of_week.id)
    if request.method == 'POST':
        template.delete()
        messages.success(request, "Template event deleted successfully")
        return redirect('schedule', day_id=day.id) 
    return redirect('schedule', day_id=template.day_of_week.id)


@login_required
def edit_template_event(request, template_id):
    template = get_object_or_404(TemplateEvent, pk=template_id)

    if request.method == 'POST':
        form = TemplateEventForm(request.POST, instance=template, user=request.user, day_id=template.day_of_week.id)
        if form.is_valid():
            form.save()
            messages.success(request, "Template updated successfully")
            return redirect('schedule', day_id=template.day_of_week.id) 
    else:
        form = TemplateEventForm(instance=template, user=request.user, day_id=template.day_of_week.id)

    return render(request, "booking/edit_template_event.html", {
        'form': form,
        'template': template,
    })



@login_required
def view_template_event(request, template_id):
    template_event = get_object_or_404(TemplateEvent, id=template_id)

    # Optional: Check if user is the coach who created it
    if check_for_coach(request) == False:
        messages.error(request, "You are not authorized to view this template event.")
        return redirect('schedule', day_id=template_event.day_of_week.id)

    return render(request, 'booking/view_template_event.html', {
        'template_event': template_event,
        'is_coach': True,
    })


@login_required
def duplicate_template_schedule(request, source_day_id):
    source_day = get_object_or_404(Day, id=source_day_id)

    if check_for_coach(request) == False:
        # If the user is not a coach, redirect with an error message
        messages.error(request, "You are not authorized to duplicate this schedule.")
        return redirect('schedule', day_id=source_day.id)

    if request.method == 'POST':
        form = DuplicateTemplateDayForm(request.POST, user=request.user)
        if form.is_valid():
            target_day = form.cleaned_data['target_day']

            # Clear existing template events for target day
            TemplateEvent.objects.filter(day_of_week=target_day).delete()

            # Duplicate template events
            source_events = TemplateEvent.objects.filter(day_of_week=source_day)
            new_events = [
                TemplateEvent(
                    coach=event.coach,
                    day_of_week=target_day,
                    event_name=event.event_name,
                    description=event.description,
                    venue=event.venue,
                    start_time=event.start_time,
                    end_time=event.end_time,
                    capacity=event.capacity,
                )
                for event in source_events
            ]
            TemplateEvent.objects.bulk_create(new_events)

            messages.success(
                request,
                f"Successfully duplicated {len(new_events)} template event(s) from {source_day} to {target_day}."
            )
            return redirect('schedule', day_id=target_day.id)
    else:
        form = DuplicateTemplateDayForm(user=request.user)

    return render(
        request,
        'booking/duplicate_template_schedule.html',
        {
            'form': form,
            'source_day': source_day,
        }
    )

@login_required
def generate_schedule_view(request):
    if not check_for_coach(request):
        messages.error(request, "You are not authorized to generate a schedule.")
        return redirect('event_search', date=date.today())
    # Ensure the user is a coach
    company = request.user.profile.company

    created = generate_schedule_for_next_30_days(company)
    messages.success(request, f"{created} events created for the next 30 days.")

    return redirect('coach_dashboard')  # or wherever you want to go after

@login_required
def delete_future_events(request):
    if request.method == "POST":
        form = BulkDeleteEventsForm(request.POST)
        if form.is_valid():
            start = form.cleaned_data["start_date"]
            end = form.cleaned_data["end_date"]

            deleted, _ = Event.objects.filter(
                date_of_event__range=(start, end),
                status=0  # Future events only
            ).delete()

            messages.success(request, f"{deleted} future event(s) deleted.")
            return redirect("coach_dashboard")  # Adjust as needed
    else:
        form = BulkDeleteEventsForm()

    return render(request, "booking/delete_events.html", {"form": form})

@login_required
def switch_auto_update_status(request):
    if request.user.profile.company.manager == request.user:
        try:
            company = request.user.profile.company
            if company.auto_updates == False:
                company.auto_updates = True
            else:
                company.auto_updates = False
            company.save()  # Save the changes to the database
            messages.success(request, "Auto-update status toggled successfully.")
            return redirect('coach_dashboard')
        except Exception as e:
            messages.error(request, "An error occurred while toggling auto updates.")
            return redirect('coach_dashboard')
    else:
        messages.error(request, "You are not authorized to change this setting.")
        return redirect('event_search', date=date.today())

@login_required
def mark_coach_no_show(request, event_id):
    event = get_object_or_404(Event, pk=event_id)

    if request.user != event.coach.coach:
        messages.error(request, "You do not have permission to update this event.")
        return redirect('event_search', date=event.date_of_event)

    event.coach_no_show = True
    event.save()

    # Find used tokens for this event and mark them as unused
    used_tokens = Token.objects.filter(booking__event=event, used=True)
    for token in used_tokens:
        token.used = False
        token.save()

    messages.success(request, "Marked as coach no-show and tokens reset.")
    return redirect('event_search', date=event.date_of_event)