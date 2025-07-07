from django.db import models
from django.contrib.auth.models import User
from cloudinary.models import CloudinaryField

class Image(models.Model):
    name = models.CharField(max_length=100, unique=True)
    image = CloudinaryField('image')

    def __str__(self):
        return f"Image {self.id}: {self.name}"


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
    auto_updates = models.BooleanField(default=False)
    token_price = models.DecimalField(max_digits=8, decimal_places=2, default=5.00)
        # --- TWO FIELDS FOR STRIPE CONNECT ---
    stripe_account_id = models.CharField(max_length=255, blank=True, null=True,
                                         help_text="Stripe Connect Account ID for this company.")
    stripe_onboarding_completed = models.BooleanField(default=False)

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
    


class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    company = models.ForeignKey(Company, on_delete=models.SET_NULL, null=True, blank=True)
    token_count = models.IntegerField(default=0)

    def __str__(self):
        company_name = self.company.name if self.company else "No Company"
        return f"{self.user.username} - {company_name}"
    

    
# TokenPurchase model - to track token purchases by users
class TokenPurchase(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    company = models.ForeignKey(Company, on_delete=models.CASCADE)
    tokens_bought = models.PositiveIntegerField()
    total_price = models.DecimalField(max_digits=8, decimal_places=2)
    timestamp = models.DateTimeField(auto_now_add=True)
    stripe_payment_intent_id = models.CharField(max_length=255, blank=True, null=True)

    def get_cost_per_token(self):
        return self.total_price / self.tokens_bought if self.tokens_bought > 0 else 0
    


    def __str__(self):
        return f"{self.user} bought {self.tokens_bought} token(s) from {self.company}"
    

class Token(models.Model):
    id = models.AutoField(primary_key=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='tokens')
    company = models.ForeignKey(Company, on_delete=models.CASCADE)
    purchased_on = models.DateTimeField(auto_now_add=True)
    purchase = models.ForeignKey(
       TokenPurchase, on_delete=models.CASCADE, null=True, blank=True, default=None)
    used = models.BooleanField(default=False)
    refunded = models.BooleanField(default=False)
    booking = models.ForeignKey(
    'booking.Booking', on_delete=models.SET_NULL,
    null=True, blank=True, related_name='used_token'
)

    def __str__(self):
        return f"Token for {self.user.username} - Used: {self.used}"

class RefundRequest(models.Model):
    STATUS_CHOICES = [
        ('Pending', 'Pending'),
        ('Approved', 'Approved'),
        ('Denied', 'Denied'),
    ]

    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name='refund_requests'
    )
    token = models.ForeignKey(
        Token, on_delete=models.CASCADE, related_name='refund_requests'
    )
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default='Pending'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    reviewed_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True, related_name='reviewed_refunds'
    )

    def __str__(self):
        return f"RefundRequest for Token {self.token.id} - Status: {self.status}"

