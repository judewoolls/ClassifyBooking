from django.contrib import admin
from .models import Company, Venue, Coach, UserProfile, Token, RefundRequest

# Register your models here.
admin.site.register(Company)
admin.site.register(Venue)
admin.site.register(UserProfile)
admin.site.register(Token)
admin.site.register(RefundRequest)