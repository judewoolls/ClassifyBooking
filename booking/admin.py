from django.contrib import admin
from .models import Event, Booking, Coach

# Register your models here.
admin.site.register(Event)
admin.site.register(Booking)
admin.site.register(Coach)