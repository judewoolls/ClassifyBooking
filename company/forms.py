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