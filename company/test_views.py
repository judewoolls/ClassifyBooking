from django.test import TestCase
from django.urls import reverse
from django.contrib.auth.models import User
from company.models import Company, Coach
from django.contrib.messages import get_messages
from company.forms import AddCoachForm, ChangeCompanyDetailsForm, CreateCompanyForm, RemoveCoachForm

class ViewClientsViewTest(TestCase):
    def setUp(self):
        # Create a manager user and their company
        self.manager_user = User.objects.create_user(username='manager', password='testpass')
        self.company = Company.objects.create(name="Test Company", manager=self.manager_user)
        self.manager_user.profile.company = self.company
        self.manager_user.profile.save()

        # Create a regular client user
        self.client_user = User.objects.create_user(username='client', password='testpass')
        self.client_user.profile.company = self.company
        self.client_user.profile.save()

        # Create a coach user
        self.coach_user = User.objects.create_user(username='coach', password='testpass')
        Coach.objects.create(coach=self.coach_user, company=self.company)

        # URL for the view
        self.url = reverse('view_clients')

    def test_redirect_if_not_logged_in(self):
        """Test that unauthenticated users are redirected to the login page."""
        response = self.client.get(self.url)
        login_url = reverse('account_login')
        self.assertRedirects(response, f"{login_url}?next={self.url}")

    def test_view_clients_with_clients(self):
        """Test that the view displays clients when they exist."""
        self.client.login(username='manager', password='testpass')
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'company/view_clients.html')
        self.assertContains(response, 'Found 1 clients for your company.')
        self.assertContains(response, 'client')

    def test_view_clients_no_clients(self):
        """Test that the view displays a message when no clients exist."""
        # Remove all clients except the manager and coach
        User.objects.filter(profile__company=self.company).exclude(id=self.manager_user.id).exclude(id=self.coach_user.id).delete()

        self.client.login(username='manager', password='testpass')
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'company/view_clients.html')
        messages = list(get_messages(response.wsgi_request))
        self.assertTrue(any('No clients found for your company.' in str(m) for m in messages))


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


class ChangeCompanyDetailsViewTest(TestCase):
    def setUp(self):
        # Create a user and their profile
        self.user = User.objects.create_user(username='testuser', password='testpass')

        # Create a company and associate it with the user
        self.company = Company.objects.create(name="Test Company", manager=self.user)
        self.user.profile.company = self.company
        self.user.profile.save()

        # URL for the change company details view
        self.url = reverse('change_company_details')

    def test_redirect_if_not_logged_in(self):
        """Test that unauthenticated users are redirected to the login page."""
        response = self.client.get(self.url)
        login_url = reverse('account_login')
        self.assertRedirects(response, f"{login_url}?next={self.url}")

    def test_get_change_company_details_form(self):
        """Test that the form is displayed for authenticated users."""
        self.client.login(username='testuser', password='testpass')
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'company/change_company_details.html')
        self.assertIsInstance(response.context['form'], ChangeCompanyDetailsForm)
        self.assertEqual(response.context['form'].instance, self.company)

    def test_post_valid_change_company_details_form(self):
        """Test that valid form submission updates the company details."""
        self.client.login(username='testuser', password='testpass')
        form_data = {
            'name': 'Updated Company Name',
            'address': '123 Test Street',
            'city': 'Test City',
            'postcode': '12345',
            'phone_number': '1234567890',
            'email': 'testcompany@example.com',
            'website': 'https://www.testcompany.com',
        }
        response = self.client.post(self.url, data=form_data)

        # Check for the redirect
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('company_dashboard'))

        # Verify the company details were updated
        self.company.refresh_from_db()
        self.assertEqual(self.company.name, 'Updated Company Name')
        self.assertEqual(self.company.address, '123 Test Street')
        self.assertEqual(self.company.city, 'Test City')
        self.assertEqual(self.company.postcode, '12345')
        self.assertEqual(self.company.phone_number, '1234567890')
        self.assertEqual(self.company.email, 'testcompany@example.com')
        self.assertEqual(self.company.website, 'https://www.testcompany.com')

    def test_post_invalid_change_company_details_form(self):
        """Test that invalid form submission does not update the company details."""
        self.client.login(username='testuser', password='testpass')
        form_data = {
            'name': '',  # Invalid data (empty name)
        }
        response = self.client.post(self.url, data=form_data)

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'company/change_company_details.html')
        self.assertContains(response, 'Form is not Valid')
        self.company.refresh_from_db()
        self.assertEqual(self.company.name, 'Test Company')  # Ensure the name is unchanged


class ViewCoachesViewTest(TestCase):
    def setUp(self):
        # Create a manager user and their company
        self.manager_user = User.objects.create_user(username='manager', password='testpass')
        self.company = Company.objects.create(name="Test Company", manager=self.manager_user)
        self.manager_user.profile.company = self.company
        self.manager_user.profile.save()

        # Create a coach user
        self.coach_user = User.objects.create_user(username='coach', password='testpass')
        Coach.objects.create(coach=self.coach_user, company=self.company)

        # URL for the view
        self.url = reverse('view_coaches')

    def test_redirect_if_not_logged_in(self):
        """Test that unauthenticated users are redirected to the login page."""
        response = self.client.get(self.url)
        login_url = reverse('account_login')
        self.assertRedirects(response, f"{login_url}?next={self.url}")

    def test_view_coaches_with_coaches(self):
        """Test that the view displays coaches when they exist."""
        self.client.login(username='manager', password='testpass')
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'company/view_coaches.html')
        self.assertContains(response, 'Found 1 coaches for your company.')
        self.assertContains(response, 'coach')

    def test_view_coaches_no_coaches(self):
        """Test that the view displays a message when no coaches exist."""
        # Remove all coaches
        Coach.objects.all().delete()

        self.client.login(username='manager', password='testpass')
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'company/view_coaches.html')
        messages = list(get_messages(response.wsgi_request))
        self.assertTrue(any('No coaches found for your company.' in str(m) for m in messages))

class AddCoachViewTest(TestCase):
    def setUp(self):
        # Create a manager user and their company
        self.manager_user = User.objects.create_user(username='manager', password='testpass')
        self.company = Company.objects.create(name="Test Company", manager=self.manager_user)
        self.manager_user.profile.company = self.company
        self.manager_user.profile.save()

        # Create a user who can be added as a coach
        self.new_coach_user = User.objects.create_user(username='newcoach', password='testpass')
        self.new_coach_user.profile.company = self.company
        self.new_coach_user.profile.save()

        # URL for the add coach view
        self.url = reverse('add_coach')

    def test_redirect_if_not_logged_in(self):
        """Test that unauthenticated users are redirected to the login page."""
        response = self.client.get(self.url)
        login_url = reverse('account_login')
        self.assertRedirects(response, f"{login_url}?next={self.url}")

    def test_get_add_coach_form(self):
        """Test that the add coach form is displayed for authenticated users."""
        self.client.login(username='manager', password='testpass')
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'company/add_coach.html')
        self.assertIsInstance(response.context['form'], AddCoachForm)

    def test_post_valid_add_coach_form(self):
        """Test that a valid form submission adds a new coach."""
        self.client.login(username='manager', password='testpass')
        form_data = {'coach': self.new_coach_user.id}
        response = self.client.post(self.url, data=form_data)

        # Check for the redirect
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('company_dashboard'))

        # Verify the coach was added
        self.assertTrue(Coach.objects.filter(coach=self.new_coach_user, company=self.company).exists())

        # Check for the success message
        messages = list(get_messages(response.wsgi_request))
        self.assertTrue(any('Coach added successfully.' in str(m) for m in messages))

    def test_post_invalid_add_coach_form(self):
        """Test that an invalid form submission does not add a coach."""
        self.client.login(username='manager', password='testpass')
        form_data = {'coach': ''}  # Invalid data
        response = self.client.post(self.url, data=form_data)

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'company/add_coach.html')
        self.assertFalse(Coach.objects.filter(company=self.company).exists())

        # Check for the error message
        self.assertContains(response, 'This field is required.')  # Check if the error is rendered in the template

class RemoveCoachViewTest(TestCase):
    def setUp(self):
        # Create a manager user and their company
        self.manager_user = User.objects.create_user(username='manager', password='testpass')
        self.company = Company.objects.create(name="Test Company", manager=self.manager_user)
        self.manager_user.profile.company = self.company
        self.manager_user.profile.save()

        # Create a coach user
        self.coach_user = User.objects.create_user(username='coach', password='testpass')
        self.coach = Coach.objects.create(coach=self.coach_user, company=self.company)

        # URL for the remove coach view
        self.url = reverse('remove_coach')

    def test_redirect_if_not_logged_in(self):
        """Test that unauthenticated users are redirected to the login page."""
        response = self.client.get(self.url)
        login_url = reverse('account_login')
        self.assertRedirects(response, f"{login_url}?next={self.url}")

    def test_get_remove_coach_form(self):
        """Test that the remove coach form is displayed for authenticated users."""
        self.client.login(username='manager', password='testpass')
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'company/remove_coach.html')
        self.assertIsInstance(response.context['form'], RemoveCoachForm)

    def test_post_valid_remove_coach_form(self):
        """Test that a valid form submission removes a coach."""
        self.client.login(username='manager', password='testpass')
        form_data = {'coach': self.coach.id}
        response = self.client.post(self.url, data=form_data)

        # Check for the redirect
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('company_dashboard'))

        # Verify the coach was removed
        self.assertFalse(Coach.objects.filter(id=self.coach.id).exists())

        # Check for the success message
        messages = list(get_messages(response.wsgi_request))
        self.assertTrue(any(f'Coach: {self.coach} removed successfully.' in str(m) for m in messages))

    def test_post_invalid_remove_coach_form(self):
        """Test that an invalid form submission does not remove a coach."""
        self.client.login(username='manager', password='testpass')
        form_data = {'coach': ''}  # Invalid data
        response = self.client.post(self.url, data=form_data)

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'company/remove_coach.html')
        self.assertTrue(Coach.objects.filter(id=self.coach.id).exists())  # Coach should still exist
        self.assertContains(response, 'This field is required.')  # Check if the error is rendered in the template