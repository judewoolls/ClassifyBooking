from django.db import models
from django.db import models
from django.contrib.auth.models import User


class Company(models.Model):
    company_id = models.AutoField(primary_key=True, unique=True) #  Same as above
    manager = models.ForeignKey(User, on_delete=models.CASCADE, related_name='company_manager')
    name = models.CharField(max_length=200)
    address = models.CharField(max_length=200)
    city = models.CharField(max_length=100)
    postcode = models.CharField(max_length=200) # Inconsistent max_length with Venue
    phone_number = models.CharField(max_length=20)
    email = models.EmailField()
    website = models.URLField()

    def __str__(self):
        return self.name
    
# Coach model - to store which users are coaches
class Coach(models.Model):
    coach = models.ForeignKey(User, on_delete=models.CASCADE,
                              related_name="coach")
    company = models.ForeignKey(
        "company.Company", on_delete=models.CASCADE, related_name="company_coach"
    )
    join_date = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.coach.username}"

# Venue model - to store the venues where the events are held
class Venue(models.Model):
    venue_id = models.AutoField(primary_key=True, unique=True) # Django automatically creates an 'id' field, so you don't need to specify it.  If you do, be consistent.
    name = models.CharField(max_length=200)
    address = models.CharField(max_length=200)
    city = models.CharField(max_length=100)
    postcode = models.CharField(max_length=20)
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='venues')

    def __str__(self):
        return f"{self.name}, {self.city}, {self.postcode}"