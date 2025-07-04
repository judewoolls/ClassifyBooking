from django.db import models
from django.contrib.auth.models import User
from company.models import Coach, Venue

STATUS = ((0, 'Active'), (1, 'Expired'))
EVENT_STATUS = ((0, 'Future'), (1, 'Past'))

# Create your models here.


# Event model - to store the events created by the coaches
class Event(models.Model):
    id = models.AutoField(primary_key=True, unique=True)
    coach = models.ForeignKey(
        Coach, on_delete=models.CASCADE, related_name="coach_on_booking"
    )
    event_name = models.CharField(max_length=200)
    description = models.TextField()
    date_of_event = models.DateField()
    from company.models import Venue
    venue = models.ForeignKey(
        Venue, on_delete=models.CASCADE, related_name="event_venue"
    )
    capacity = models.IntegerField()
    start_time = models.TimeField()
    end_time = models.TimeField()
    status = models.IntegerField(choices=EVENT_STATUS)
    coach_no_show = models.BooleanField(default=False)


    def number_of_bookings(self):
        return self.event_booking.count()

    def is_full(self):
        return self.number_of_bookings() >= self.capacity

    def is_user_booked(self, user):
        return self.event_booking.filter(user=user).exists()

    def __str__(self):
        return f"{self.event_name}: {self.date_of_event} @ {self.start_time}"


# Booking model - to store the bookings made by the users
class Booking(models.Model):
    id = models.AutoField(primary_key=True, unique=True)
    event = models.ForeignKey(
        Event, on_delete=models.CASCADE, related_name="event_booking"
    )
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="user_booking"
    )
    created_on = models.DateTimeField(auto_now_add=True)
    status = models.IntegerField(choices=STATUS, default=0)

    def __str__(self):
        return f"{STATUS[self.status][1]} #{self.id} by {self.user.username}"

    class Meta:
        ordering = ["status"]

class Day(models.Model):
    id = models.AutoField(primary_key=True, unique=True)
    day = models.CharField(max_length=20)

    def __str__(self):
        return self.day

    class Meta:
        ordering = ["id"]


class TemplateEvent(models.Model):
    coach = models.ForeignKey(Coach, on_delete=models.CASCADE, related_name="template_events")
    venue = models.ForeignKey(Venue, on_delete=models.CASCADE, related_name="template_venue")
    event_name = models.CharField(max_length=200)
    description = models.TextField()
    day_of_week = models.ForeignKey(Day, on_delete=models.CASCADE)
    start_time = models.TimeField()
    end_time = models.TimeField()
    capacity = models.PositiveIntegerField()
    active = models.BooleanField(default=True)  # To allow pausing automation

    def __str__(self):
        return f"{self.event_name} on {self.day_of_week}"

class ExcludedDate(models.Model):
    coach = models.ForeignKey(Coach, on_delete=models.CASCADE)
    date = models.DateField()

    def __str__(self):
        return f"Excluded: {self.date} by {self.coach}"

