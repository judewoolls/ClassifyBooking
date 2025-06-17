from django.contrib import admin
from .models import Event, Booking, Coach, Day, TemplateEvent, ExcludedDate

# Register your models here.
admin.site.register(Event)
admin.site.register(Booking)
admin.site.register(Coach)
admin.site.register(Day)
admin.site.register(TemplateEvent)
admin.site.register(ExcludedDate)
