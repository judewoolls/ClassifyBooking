from django.utils import timezone
from datetime import datetime, time, timedelta, date
from .models import TemplateEvent, Event, Coach, Day

def update_event_status_if_needed(event):
    now = timezone.now()  # Always returns a timezone-aware datetime

    # Combine the event date and start time
    event_start = datetime.combine(event.date_of_event, event.start_time)

    # Make sure it's timezone-aware
    if timezone.is_naive(event_start):
        event_start = timezone.make_aware(event_start)

    if event.status == 0 and now >= event_start:  # 0 == Future
        event.status = 1  # Past
        event.save(update_fields=['status'])


def generate_schedule_for_date(company, target_date):
    created_count = 0
    weekday = target_date.weekday()

    try:
        day_obj = Day.objects.get(id=weekday + 1)  # Your Day model uses id 1=Monday, etc.
    except Day.DoesNotExist:
        return 0  # No matching weekday in DB

    for coach in Coach.objects.filter(company=company):
        # Skip excluded dates
        # if ExcludedDate.objects.filter(coach=coach, date=target_date).exists():
        #     continue

        templates = TemplateEvent.objects.filter(
            coach=coach,
            day_of_week=day_obj,
            active=True
        )

        for tpl in templates:
            event_exists = Event.objects.filter(
                coach=coach,
                venue=tpl.venue,
                event_name=tpl.event_name,
                date_of_event=target_date,
                start_time=tpl.start_time,
                end_time=tpl.end_time
            ).exists()

            if not event_exists:
                Event.objects.create(
                    coach=coach,
                    venue=tpl.venue,
                    event_name=tpl.event_name,
                    description=tpl.description,
                    date_of_event=target_date,
                    start_time=tpl.start_time,
                    end_time=tpl.end_time,
                    capacity=tpl.capacity,
                    status=0  # Future
                )
                created_count += 1

    return created_count

def generate_schedule_for_next_30_days(company):
    today = date.today()
    total_created = 0
    for offset in range(30):
        day = today + timedelta(days=offset)
        total_created += generate_schedule_for_date(company, day)
    return total_created


def generate_schedule_for_day_30(company):
    target = date.today() + timedelta(days=30)
    return generate_schedule_for_date(company, target)
