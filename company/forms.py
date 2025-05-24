from allauth.account.forms import SignupForm
from django import forms
from django.contrib.auth.models import User
from company.models import Company, Coach

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

