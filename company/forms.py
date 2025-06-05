from allauth.account.forms import SignupForm
from django import forms
from django.contrib.auth.models import User
from company.models import Company, Coach, Venue, Token

class CustomSignupForm(SignupForm):
    company = forms.ModelChoiceField(queryset=Company.objects.all(), empty_label="Select your company", required=False)

    def save(self, request):
        user = super().save(request)
        company = self.cleaned_data['company']
        user.profile.company = company
        user.profile.save()
        return user
    
class CreateCompanyForm(forms.ModelForm):
    class Meta:
        model = Company
        fields = ['name', 'address', 'city', 'postcode', 'phone_number', 'email', 'website']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'address': forms.TextInput(attrs={'class': 'form-control'}),
            'city': forms.TextInput(attrs={'class': 'form-control'}),
            'postcode': forms.TextInput(attrs={'class': 'form-control'}),
            'phone_number': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'website': forms.URLInput(attrs={'class': 'form-control'}),
        }

    def save(self, commit=True):
        company = super().save(commit=False)
        if commit:
            company.save()
        return company
    
class ChangeCompanyDetailsForm(forms.ModelForm):
    class Meta:
        model = Company
        fields = ['name', 'address', 'city', 'postcode', 'phone_number', 'email', 'website']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'address': forms.TextInput(attrs={'class': 'form-control'}),
            'city': forms.TextInput(attrs={'class': 'form-control'}),
            'postcode': forms.TextInput(attrs={'class': 'form-control'}),
            'phone_number': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'website': forms.URLInput(attrs={'class': 'form-control'}),
        }
    def save(self, commit=True):
        company = super().save(commit=False)
        if commit:
            company.save()
        return company
    
class AddCoachForm(forms.Form):
    coach = forms.ModelChoiceField(queryset=User.objects.none(), label="Select Coach", required=True)

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user')  # Expect the current user to be passed in
        super().__init__(*args, **kwargs)

        if hasattr(user, 'profile') and user.profile.company:
            company = user.profile.company

            # Get users in the same company
            company_users = User.objects.filter(
                profile__company=company,
                is_active=True
            ).exclude(id=user.id)

            # Exclude users who are already coaches
            coached_user_ids = Coach.objects.filter(company=company).values_list('coach__id', flat=True)
            available_users = company_users.exclude(id__in=coached_user_ids)

            self.fields['coach'].queryset = available_users

    def save(self, company):
        coach = self.cleaned_data['coach']
        if not Coach.objects.filter(coach=coach, company=company).exists():
            Coach.objects.create(coach=coach, company=company)
        return coach


class RemoveCoachForm(forms.Form):
    coach = forms.ModelChoiceField(queryset=Coach.objects.none(), label="Select Coach", required=True)

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user')  # Expect the current user to be passed in
        super().__init__(*args, **kwargs)

        if hasattr(user, 'profile') and user.profile.company:
            company = user.profile.company

            # Get coaches in the same company
            self.fields['coach'].queryset = Coach.objects.filter(company=company).exclude(coach__id=user.id)

    def save(self, company):
        coach = self.cleaned_data['coach']
        coach.delete()
        return coach

class AddVenueForm(forms.ModelForm):
    class Meta:
        model = Venue
        fields = ['name', 'address', 'city', 'postcode']

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)  # Extract the 'user' argument
        super().__init__(*args, **kwargs)
        if user and hasattr(user, 'profile') and user.profile.company:
            # Optionally customize the form based on the user
            self.fields['name'].widget.attrs.update({'placeholder': 'Enter venue name'})

    def save(self, commit=True):
        venue = super().save(commit=False)
        if commit:
            venue.save()
        return venue

class EditVenueForm(forms.Form):
    name = forms.CharField(max_length=200, label="Venue Name", required=True)
    address = forms.CharField(max_length=200, label="Address", required=True)
    city = forms.CharField(max_length=100, label="City", required=True)
    postcode = forms.CharField(max_length=20, label="Postcode", required=True)

    def __init__(self, *args, **kwargs):
        self.venue_id = kwargs.pop('venue_id', None)
        super().__init__(*args, **kwargs)

        if self.venue_id:
            venue = Venue.objects.get(venue_id=self.venue_id)  # Use venue_id here
            self.fields['name'].initial = venue.name
            self.fields['address'].initial = venue.address
            self.fields['city'].initial = venue.city
            self.fields['postcode'].initial = venue.postcode

    def save(self):
        venue = Venue.objects.get(venue_id=self.venue_id)  # Use venue_id here
        venue.name = self.cleaned_data['name']
        venue.address = self.cleaned_data['address']
        venue.city = self.cleaned_data['city']
        venue.postcode = self.cleaned_data['postcode']
        venue.save()
        return venue
    
# Tokens and purchases

class PurchaseTokenForm(forms.Form):
    token_count = forms.IntegerField(min_value=1, label="Number of Tokens", required=True)

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)  # Extract the 'user' argument
        super().__init__(*args, **kwargs)
        if user and hasattr(user, 'profile') and user.profile.company:
            self.company = user.profile.company

    def save(self):
        token_count = self.cleaned_data['token_count']
        for _ in range(token_count):
            Token.objects.create(user=self.company.manager, company=self.company)
        return token_count