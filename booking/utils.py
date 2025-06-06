from django.utils import timezone
from datetime import datetime, time

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
