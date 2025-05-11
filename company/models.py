from django.db import models
from django.db import models
from django.contrib.auth.models import User


class Company(models.Model):
    company_id = models.AutoField(primary_key=True, unique=True) #  Same as above
    name = models.CharField(max_length=200)
    address = models.CharField(max_length=200)
    city = models.CharField(max_length=100)
    postcode = models.CharField(max_length=200) # Inconsistent max_length with Venue
    phone_number = models.CharField(max_length=20)
    email = models.EmailField()
    website = models.URLField()

    def __str__(self):
        return self.name

#  It's generally recommended to use lowercase for model names (venue, company)
class Venue(models.Model):
    venue_id = models.AutoField(primary_key=True, unique=True) # Django automatically creates an 'id' field, so you don't need to specify it.  If you do, be consistent.
    name = models.CharField(max_length=200)
    address = models.CharField(max_length=200)
    city = models.CharField(max_length=100)
    postcode = models.CharField(max_length=20)
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='venues')

    def __str__(self):
        return f"{self.name}, {self.city}, {self.postcode}"