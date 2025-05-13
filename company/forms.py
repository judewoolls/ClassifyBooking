from allauth.account.forms import SignupForm
from django import forms
from company.models import Company

class CustomSignupForm(SignupForm):
    company = forms.ModelChoiceField(queryset=Company.objects.all(), empty_label="Select your company", required=False)

    def save(self, request):
        user = super().save(request)
        company = self.cleaned_data['company']
        user.profile.company = company
        user.profile.save()
        return user