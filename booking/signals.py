from django.db.models.signals import pre_delete
from django.dispatch import receiver
from .models import Booking
from company.models import Token  # Adjust path if needed

@receiver(pre_delete, sender=Booking)
def release_token_on_booking_delete(sender, instance, **kwargs):
    token = Token.objects.filter(booking=instance, used=True).first()
    event = instance.event

    if not token:
        return

    # add the event status update here

    if event.status == 0:
        token.used = False
        token.booking = None
        token.save()
    else:
        token.booking = None
        token.save()

from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver
from utils.email import send_custom_email

@receiver(post_save, sender=User)
def send_welcome_email(sender, instance, created, **kwargs):
    if created:
        send_custom_email(
            subject="Welcome to Classify Booking!",
            message=f"Hi {instance.first_name}, thanks for signing up!",
            recipient_list=[instance.email]
        )
