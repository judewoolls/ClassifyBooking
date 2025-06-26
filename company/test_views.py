from django.test import TestCase
from django.urls import reverse
from django.contrib.auth.models import User
from company.models import Company, Coach, Token
from company.forms import CreateCompanyForm

class CompanyDashboardViewTest(TestCase):
    def setUp(self):
        # Create a user and their profile
        self.user = User.objects.create_user(username='testuser', password='testpass')

        # Create a company and associate it with the user
        self.company = Company.objects.create(name="Test Company", manager=self.user)

        # Attach the company to the user's profile
        self.user.profile.company = self.company
        self.user.profile.save()

        # URL for the company dashboard
        self.url = reverse('company_dashboard')

    def test_redirect_if_not_logged_in(self):
        """Test that unauthenticated users are redirected to the login page."""
        response = self.client.get(self.url)
        login_url = reverse('account_login')
        self.assertRedirects(response, f"{login_url}?next={self.url}")

    def test_manager_sees_manager_dashboard(self):
        """Test that the manager sees the manager dashboard."""
        self.client.login(username='testuser', password='testpass')
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'company/company_manager_dashboard.html')
        self.assertEqual(response.context['company'], self.company)

    def test_coach_sees_user_dashboard(self):
        """Test that a coach sees the user dashboard."""
        # Create a coach user
        coach_user = User.objects.create_user(username='coachuser', password='testpass')
        coach_user.profile.company = self.company
        coach_user.profile.save()
        Coach.objects.create(coach=coach_user, company=self.company)

        self.client.login(username='coachuser', password='testpass')
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'company/company_user_dashboard.html')
        self.assertEqual(response.context['company'], self.company)
        self.assertIn('tokens', response.context)

    def test_user_without_company_redirects_to_create_company(self):
        """Test that a user without a company is redirected to the create company page."""
        user_without_company = User.objects.create_user(username='nocompanyuser', password='testpass')
        self.client.login(username='nocompanyuser', password='testpass')

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'company/create_company.html')
        self.assertIsInstance(response.context['create_form'], CreateCompanyForm)