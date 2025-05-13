from django.contrib import admin
from .models import Company, Venue, Coach, UserProfile

# Register your models here.
admin.site.register(Company)
admin.site.register(Venue)
admin.site.register(UserProfile)