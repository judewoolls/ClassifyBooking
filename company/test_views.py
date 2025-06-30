from django.test import TestCase
from django.urls import reverse
from django.contrib.auth.models import User
from django.contrib.auth import get_user_model
from company.models import Company, Coach, Token, Venue, RefundRequest
from django.contrib.messages import get_messages
from company.forms import AddCoachForm, ChangeCompanyDetailsForm, CreateCompanyForm, RemoveCoachForm, AddVenueForm, EditVenueForm, PurchaseTokenForm
from django.db.models import Case, When, IntegerField

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



class ClientDetailsViewTest(TestCase):
    def setUp(self):
        # Create a manager user and their company
        self.manager_user = User.objects.create_user(username='manager', password='testpass')
        self.company = Company.objects.create(name="Test Company", manager=self.manager_user)
        self.manager_user.profile.company = self.company
        self.manager_user.profile.save()

        # Create a client user
        self.client_user = User.objects.create_user(username='client', password='testpass')
        self.client_user.profile.company = self.company
        self.client_user.profile.save()

        # URL for the client details view
        self.url = reverse('client_details', args=[self.client_user.id])

    def test_redirect_if_not_logged_in(self):
        """Test that unauthenticated users are redirected to the login page."""
        response = self.client.get(self.url)
        login_url = reverse('account_login')
        self.assertRedirects(response, f"{login_url}?next={self.url}")

    def test_view_client_details_valid(self):
        """Test that the view displays client details when the client exists."""
        self.client.login(username='manager', password='testpass')
        response = self.client.post(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'company/client_details.html')
        self.assertEqual(response.context['client'], self.client_user)
        self.assertEqual(response.context['company'], self.company)

    def test_view_client_details_invalid_client(self):
        """Test that the view redirects with an error message when the client does not exist."""
        self.client.login(username='manager', password='testpass')
        invalid_url = reverse('client_details', args=[999])  # Non-existent client ID
        response = self.client.post(invalid_url)

        self.assertRedirects(response, reverse('view_clients'))
        messages = list(get_messages(response.wsgi_request))
        self.assertTrue(any('Client not found or does not belong to your company.' in str(m) for m in messages))

    def test_invalid_request_method(self):
        """Test that the view redirects with an error message for invalid request methods."""
        self.client.login(username='manager', password='testpass')
        response = self.client.get(self.url)  # GET request instead of POST

        self.assertRedirects(response, reverse('view_clients'))
        messages = list(get_messages(response.wsgi_request))
        self.assertTrue(any('Invalid request method.' in str(m) for m in messages))



class RemoveClientViewTest(TestCase):
    def setUp(self):
        # Create a manager user and their company
        self.manager_user = User.objects.create_user(username='manager', password='testpass')
        self.company = Company.objects.create(name="Test Company", manager=self.manager_user)
        self.manager_user.profile.company = self.company
        self.manager_user.profile.save()

        # Create a client user
        self.client_user = User.objects.create_user(username='client', password='testpass')
        self.client_user.profile.company = self.company
        self.client_user.profile.save()

        # URL for the remove client view
        self.url = reverse('remove_client', args=[self.client_user.id])

    def test_redirect_if_not_logged_in(self):
        """Test that unauthenticated users are redirected to the login page."""
        response = self.client.post(self.url)
        login_url = reverse('account_login')
        self.assertRedirects(response, f"{login_url}?next={self.url}")

    def test_remove_client_with_no_tokens(self):
        """Test that a client is removed successfully when they have no active tokens."""
        self.client.login(username='manager', password='testpass')
        response = self.client.post(self.url)

        self.assertRedirects(response, reverse('view_clients'))
        self.client_user.refresh_from_db()
        self.assertIsNone(self.client_user.profile.company)  # Client should no longer belong to the company

        # Check for the success message
        messages = list(get_messages(response.wsgi_request))
        self.assertTrue(any(f'Client {self.client_user.username} removed successfully.' in str(m) for m in messages))

    def test_remove_client_with_active_tokens(self):
        """Test that a client with active tokens cannot be removed."""
        self.client.login(username='manager', password='testpass')
        Token.objects.create(user=self.client_user, company=self.company, refunded=False, used=False)

        response = self.client.post(self.url)

        self.assertRedirects(response, reverse('view_clients'))
        self.client_user.refresh_from_db()
        self.assertEqual(self.client_user.profile.company, self.company)  # Client should still belong to the company

        # Check for the error message
        messages = list(get_messages(response.wsgi_request))
        self.assertTrue(any('Cannot remove client with active tokens.' in str(m) for m in messages))

    def test_remove_client_who_is_a_coach(self):
        """Test that a client who is also a coach cannot be removed."""
        self.client.login(username='manager', password='testpass')
        Coach.objects.create(coach=self.client_user, company=self.company)

        response = self.client.post(self.url)

        self.assertRedirects(response, reverse('view_clients'))
        self.client_user.refresh_from_db()
        self.assertEqual(self.client_user.profile.company, self.company)  # Client should still belong to the company

        # Check for the error message
        messages = list(get_messages(response.wsgi_request))
        self.assertTrue(any('The selected client is also a coach and cannot be removed as a client.' in str(m) for m in messages))

    def test_remove_client_not_in_company(self):
        """Test that a client not in the company cannot be removed."""
        self.client.login(username='manager', password='testpass')
        other_client = User.objects.create_user(username='other_client', password='testpass')

        url = reverse('remove_client', args=[other_client.id])
        response = self.client.post(url)

        self.assertRedirects(response, reverse('view_clients'))

        # Check for the error message
        messages = list(get_messages(response.wsgi_request))
        self.assertTrue(any('Client not found or does not belong to your company.' in str(m) for m in messages))

    def test_remove_client_permission_denied(self):
        """Test that a manager cannot remove a client they do not have permission to remove."""
        self.client.login(username='manager', password='testpass')
        other_company = Company.objects.create(name="Other Company", manager=self.manager_user)
        other_client = User.objects.create_user(username='other_client', password='testpass')
        other_client.profile.company = other_company
        other_client.profile.save()

        url = reverse('remove_client', args=[other_client.id])
        response = self.client.post(url)

        # Verify the redirection to the view clients page
        self.assertRedirects(response, reverse('view_clients'))  # Updated to match actual behavior

        # Check for the error message
        messages = list(get_messages(response.wsgi_request))
        self.assertTrue(any('Client not found or does not belong to your company.' in str(m) for m in messages))


class ViewClientTokensViewTest(TestCase):
    def setUp(self):
        # Create a manager user and their company
        self.manager_user = User.objects.create_user(username='manager', password='testpass')
        self.company = Company.objects.create(name="Test Company", manager=self.manager_user)
        self.manager_user.profile.company = self.company
        self.manager_user.profile.save()

        # Create a client user
        self.client_user = User.objects.create_user(username='client', password='testpass')
        self.client_user.profile.company = self.company
        self.client_user.profile.save()

        # Create tokens for the client
        self.token1 = Token.objects.create(user=self.client_user, company=self.company, refunded=False, used=False)
        self.token2 = Token.objects.create(user=self.client_user, company=self.company, refunded=True, used=False)

        # URL for the view client tokens view
        self.url = reverse('view_client_tokens', args=[self.client_user.id])

    def test_redirect_if_not_logged_in(self):
        """Test that unauthenticated users are redirected to the login page."""
        response = self.client.get(self.url)
        login_url = reverse('account_login')
        self.assertRedirects(response, f"{login_url}?next={self.url}")

    def test_view_client_tokens_with_tokens(self):
        """Test that the view displays tokens when they exist."""
        self.client.login(username='manager', password='testpass')
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'company/view_client_tokens.html')
        self.assertEqual(response.context['client'], self.client_user)
        self.assertEqual(response.context['company'], self.company)
        self.assertQuerysetEqual(
            response.context['tokens'],
            Token.objects.filter(user=self.client_user, company=self.company).order_by('-purchased_on'),
            transform=lambda x: x
        )
        self.assertContains(response, f'Found 2 tokens for client {self.client_user.username}.')

    def test_view_client_tokens_no_tokens(self):
        """Test that the view displays a message when no tokens exist."""
        Token.objects.filter(user=self.client_user, company=self.company).delete()

        self.client.login(username='manager', password='testpass')
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'company/view_client_tokens.html')
        self.assertContains(response, f'No tokens found for client {self.client_user.username}.')

    def test_view_client_tokens_invalid_client(self):
        """Test that the view redirects with an error message when the client does not exist."""
        self.client.login(username='manager', password='testpass')
        invalid_url = reverse('view_client_tokens', args=[999])  # Non-existent client ID
        response = self.client.get(invalid_url)

        self.assertRedirects(response, reverse('view_clients'))
        messages = list(get_messages(response.wsgi_request))
        self.assertTrue(any('Client not found or does not belong to your company.' in str(m) for m in messages))


from booking.models import Booking, Event

class ViewBookingsViewTest(TestCase):
    def setUp(self):
        # Create a manager user and their company
        self.manager_user = User.objects.create_user(username='manager', password='testpass')
        self.company = Company.objects.create(name="Test Company", manager=self.manager_user)
        self.manager_user.profile.company = self.company
        self.manager_user.profile.save()

        # Create a coach user
        self.coach_user = User.objects.create_user(username='coach', password='testpass')
        self.coach_user.profile.company = self.company
        self.coach = Coach.objects.create(coach=self.coach_user, company=self.company)
        self.coach_user.profile.save()
        Coach.objects.create(coach=self.coach_user, company=self.company)

        # Create a venue for the event
        self.venue = Venue.objects.create(
            name="Test Venue",
            address="123 Venue St",
            city="Test City",
            postcode="12345",
            company=self.company
        )

        # Create an event and bookings
        self.event = Event.objects.create(
            event_name="Test Event",
            coach=self.coach,
            date_of_event="2025-07-01",
            capacity=10,
            description="This is a test event.",
            start_time="10:00:00",
            end_time="12:00:00",
            venue=self.venue,
            status=0
        )
        self.booking1 = Booking.objects.create(event=self.event, user=self.manager_user)
        self.booking2 = Booking.objects.create(event=self.event, user=self.coach_user)

        # URL for the view bookings view
        self.url = reverse('view_bookings')

    def test_redirect_if_not_logged_in(self):
        """Test that unauthenticated users are redirected to the login page."""
        response = self.client.get(self.url)
        login_url = reverse('account_login')
        self.assertRedirects(response, f"{login_url}?next={self.url}")

    def test_view_bookings_with_bookings(self):
        """Test that the view displays bookings when they exist."""
        self.client.login(username='manager', password='testpass')
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'company/view_bookings.html')
        self.assertEqual(response.context['company'], self.company)
        self.assertQuerysetEqual(
            response.context['bookings'],
            Booking.objects.filter(event__coach__company=self.company).order_by('-event__date_of_event'),
            transform=lambda x: x
        )
        self.assertContains(response, f'Found 2 bookings for your company.')

    def test_view_bookings_no_bookings(self):
        """Test that the view displays a message when no bookings exist."""
        Booking.objects.all().delete()

        self.client.login(username='manager', password='testpass')
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'company/view_bookings.html')
        self.assertContains(response, 'No bookings found for your company.')



class ManageVenuesViewTest(TestCase):
    def setUp(self):
        # Create a manager user and their company
        self.manager_user = User.objects.create_user(username='manager', password='testpass')
        self.company = Company.objects.create(name="Test Company", manager=self.manager_user)
        self.manager_user.profile.company = self.company
        self.manager_user.profile.save()

        # Create some venues for the company
        self.venue1 = Venue.objects.create(
            name="Venue 1",
            address="123 Venue St",
            city="Test City",
            postcode="12345",
            company=self.company
        )
        self.venue2 = Venue.objects.create(
            name="Venue 2",
            address="456 Venue Ave",
            city="Another City",
            postcode="67890",
            company=self.company
        )

        # URL for the manage venues view
        self.url = reverse('manage_venues')

    def test_redirect_if_not_logged_in(self):
        """Test that unauthenticated users are redirected to the login page."""
        response = self.client.get(self.url)
        login_url = reverse('account_login')
        self.assertRedirects(response, f"{login_url}?next={self.url}")

    def test_manage_venues_with_venues(self):
        """Test that the view displays venues when they exist."""
        self.client.login(username='manager', password='testpass')
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'company/manage_venues.html')
        self.assertEqual(response.context['company'], self.company)
        self.assertQuerysetEqual(
            response.context['venues'].order_by('venue_id'),  # Explicitly order the queryset from the context
            Venue.objects.filter(company=self.company).order_by('venue_id'),  # Explicitly order the queryset from the database
            transform=lambda x: x
        )
        self.assertContains(response, f'Found 2 venues for your company.')
        self.assertContains(response, 'Venue 1')
        self.assertContains(response, 'Venue 2')

    def test_manage_venues_no_venues(self):
        """Test that the view displays a message when no venues exist."""
        Venue.objects.filter(company=self.company).delete()

        self.client.login(username='manager', password='testpass')
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'company/manage_venues.html')
        self.assertContains(response, 'Found 0 venues for your company.')

    def test_manage_venues_no_company(self):
        """Test that the view redirects with an error message if the user has no company."""
        user_without_company = User.objects.create_user(username='nocompanyuser', password='testpass')
        self.client.login(username='nocompanyuser', password='testpass')

        response = self.client.get(self.url)

        self.assertRedirects(response, reverse('company_dashboard'))
        messages = list(get_messages(response.wsgi_request))
        self.assertTrue(any('You do not have a company associated with your profile.' in str(m) for m in messages))


class ViewVenueViewTest(TestCase):
    def setUp(self):
        # Create a manager user and their company
        self.manager_user = User.objects.create_user(username='manager', password='testpass')
        self.company = Company.objects.create(name="Test Company", manager=self.manager_user)
        self.manager_user.profile.company = self.company
        self.manager_user.profile.save()

        # Create a venue for the company
        self.venue = Venue.objects.create(
            name="Test Venue",
            address="123 Venue St",
            city="Test City",
            postcode="12345",
            company=self.company
        )

        # URL for the view venue view
        self.url = reverse('view_venue', args=[self.venue.venue_id])

    def test_redirect_if_not_logged_in(self):
        """Test that unauthenticated users are redirected to the login page."""
        response = self.client.get(self.url)
        login_url = reverse('account_login')
        self.assertRedirects(response, f"{login_url}?next={self.url}")

    def test_view_venue_valid(self):
        """Test that the view displays venue details when the venue exists."""
        self.client.login(username='manager', password='testpass')
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'company/view_venue.html')
        self.assertEqual(response.context['venue'], self.venue)
        self.assertEqual(response.context['company'], self.company)
        self.assertContains(response, 'Test Venue')
        self.assertContains(response, '123 Venue St')

    def test_view_venue_invalid(self):
        """Test that the view redirects with an error message when the venue does not exist."""
        self.client.login(username='manager', password='testpass')
        invalid_url = reverse('view_venue', args=[999])  # Non-existent venue ID
        response = self.client.get(invalid_url)

        self.assertRedirects(response, reverse('manage_venues'))
        messages = list(get_messages(response.wsgi_request))
        self.assertTrue(any('Venue not found or does not belong to your company.' in str(m) for m in messages))


class AddVenueViewTest(TestCase):
    def setUp(self):
        # Create a manager user and their company
        self.manager_user = User.objects.create_user(username='manager', password='testpass')
        self.company = Company.objects.create(name="Test Company", manager=self.manager_user)
        self.manager_user.profile.company = self.company
        self.manager_user.profile.save()

        # URL for the add venue view
        self.url = reverse('add_venue')

    def test_redirect_if_not_logged_in(self):
        """Test that unauthenticated users are redirected to the login page."""
        response = self.client.get(self.url)
        login_url = reverse('account_login')
        self.assertRedirects(response, f"{login_url}?next={self.url}")

    def test_get_add_venue_form(self):
        """Test that the add venue form is displayed for authenticated users."""
        self.client.login(username='manager', password='testpass')
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'company/add_venue.html')
        self.assertIsInstance(response.context['form'], AddVenueForm)

    def test_post_valid_add_venue_form(self):
        """Test that a valid form submission adds a new venue."""
        self.client.login(username='manager', password='testpass')
        form_data = {
            'name': 'New Venue',
            'address': '123 Venue St',
            'city': 'Test City',
            'postcode': '12345',
        }
        response = self.client.post(self.url, data=form_data)

        # Check for the redirect
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('manage_venues'))

        # Verify the venue was added
        self.assertTrue(Venue.objects.filter(name='New Venue', company=self.company).exists())

        # Check for the success message
        messages = list(get_messages(response.wsgi_request))
        self.assertTrue(any('Venue added successfully.' in str(m) for m in messages))

    def test_post_invalid_add_venue_form(self):
        """Test that an invalid form submission does not add a venue."""
        self.client.login(username='manager', password='testpass')
        form_data = {
            'name': '',  # Invalid data (empty name)
            'address': '123 Venue St',
            'city': 'Test City',
            'postcode': '12345',
        }
        response = self.client.post(self.url, data=form_data)

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'company/add_venue.html')
        self.assertFalse(Venue.objects.filter(company=self.company).exists())

        # Check for the error message
        self.assertContains(response, 'Form is invalid. Please correct the errors.')

    def test_add_venue_no_company(self):
        """Test that a user without a company cannot add a venue."""
        user_without_company = User.objects.create_user(username='nocompanyuser', password='testpass')
        self.client.login(username='nocompanyuser', password='testpass')

        response = self.client.get(self.url)

        self.assertRedirects(response, reverse('company_dashboard'))
        messages = list(get_messages(response.wsgi_request))
        self.assertTrue(any('You do not have a company associated with your profile.' in str(m) for m in messages))


class RemoveVenueViewTest(TestCase):
    def setUp(self):
        # Create a manager user and their company
        self.manager_user = User.objects.create_user(username='manager', password='testpass')
        self.company = Company.objects.create(name="Test Company", manager=self.manager_user)
        self.manager_user.profile.company = self.company
        self.manager_user.profile.save()

        # Create a venue for the company
        self.venue = Venue.objects.create(
            name="Test Venue",
            address="123 Venue St",
            city="Test City",
            postcode="12345",
            company=self.company
        )

        # Create a coach user and associate it with the company
        self.coach_user = User.objects.create_user(username='coach', password='testpass')
        self.coach = Coach.objects.create(coach=self.coach_user, company=self.company)

        # Create events and bookings associated with the venue
        self.event1 = Event.objects.create(
            event_name="Event 1",
            coach=self.coach,
            date_of_event="2025-07-01",
            capacity=10,
            description="Test Event 1",
            start_time="10:00:00",
            end_time="12:00:00",
            venue=self.venue,
            status=0
        )
        self.event2 = Event.objects.create(
            event_name="Event 2",
            coach=self.coach,
            date_of_event="2025-07-02",
            capacity=20,
            description="Test Event 2",
            start_time="14:00:00",
            end_time="16:00:00",
            venue=self.venue,
            status=0
        )
        Booking.objects.create(event=self.event1, user=self.manager_user)
        Booking.objects.create(event=self.event2, user=self.manager_user)

        # URL for the remove venue view
        self.url = reverse('remove_venue', args=[self.venue.venue_id])

    def test_redirect_if_not_logged_in(self):
        """Test that unauthenticated users are redirected to the login page."""
        response = self.client.post(self.url)
        login_url = reverse('account_login')
        self.assertRedirects(response, f"{login_url}?next={self.url}")

    def test_remove_venue_valid(self):
        """Test that a venue is removed successfully along with its events and bookings."""
        self.client.login(username='manager', password='testpass')
        response = self.client.post(self.url)

        self.assertRedirects(response, reverse('manage_venues'))

        # Check that the venue, events, and bookings are deleted
        self.assertFalse(Venue.objects.filter(venue_id=self.venue.venue_id).exists())
        self.assertFalse(Event.objects.filter(venue=self.venue).exists())
        self.assertFalse(Booking.objects.filter(event__venue=self.venue).exists())

        # Check for the success message
        messages = list(get_messages(response.wsgi_request))
        self.assertTrue(any(
            f'Venue "{self.venue.name}" removed. 2 events and 2 bookings were deleted.' in str(m)
            for m in messages
        ))

    def test_remove_venue_invalid(self):
        """Test that attempting to remove a non-existent venue shows an error message."""
        self.client.login(username='manager', password='testpass')
        invalid_url = reverse('remove_venue', args=[999])  # Non-existent venue ID
        response = self.client.post(invalid_url)

        self.assertRedirects(response, reverse('manage_venues'))

        # Check for the error message
        messages = list(get_messages(response.wsgi_request))
        self.assertTrue(any('Venue not found or does not belong to your company.' in str(m) for m in messages))

    def test_remove_venue_not_in_company(self):
        """Test that a venue not belonging to the user's company cannot be removed."""
        other_company = Company.objects.create(name="Other Company", manager=self.manager_user)
        other_venue = Venue.objects.create(
            name="Other Venue",
            address="456 Other St",
            city="Other City",
            postcode="67890",
            company=other_company
        )

        self.client.login(username='manager', password='testpass')
        url = reverse('remove_venue', args=[other_venue.venue_id])
        response = self.client.post(url)

        self.assertRedirects(response, reverse('manage_venues'))

        # Check that the venue still exists
        self.assertTrue(Venue.objects.filter(venue_id=other_venue.venue_id).exists())

        # Check for the error message
        messages = list(get_messages(response.wsgi_request))
        self.assertTrue(any('Venue not found or does not belong to your company.' in str(m) for m in messages))


class EditVenueViewTest(TestCase):
    def setUp(self):
        # Create a manager user and their company
        self.manager_user = User.objects.create_user(username='manager', password='testpass')
        self.company = Company.objects.create(name="Test Company", manager=self.manager_user)
        self.manager_user.profile.company = self.company
        self.manager_user.profile.save()

        # Create a venue for the company
        self.venue = Venue.objects.create(
            name="Test Venue",
            address="123 Venue St",
            city="Test City",
            postcode="12345",
            company=self.company
        )

        # URL for the edit venue view
        self.url = reverse('edit_venue', args=[self.venue.venue_id])

    def test_redirect_if_not_logged_in(self):
        """Test that unauthenticated users are redirected to the login page."""
        response = self.client.get(self.url)
        login_url = reverse('account_login')
        self.assertRedirects(response, f"{login_url}?next={self.url}")

    def test_get_edit_venue_form(self):
        """Test that the edit venue form is displayed for authenticated users."""
        self.client.login(username='manager', password='testpass')
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'company/edit_venue.html')
        self.assertIsInstance(response.context['form'], EditVenueForm)
        self.assertEqual(response.context['venue'], self.venue)

    def test_post_valid_edit_venue_form(self):
        """Test that a valid form submission updates the venue."""
        self.client.login(username='manager', password='testpass')
        form_data = {
            'name': 'Updated Venue',
            'address': '456 Updated St',
            'city': 'Updated City',
            'postcode': '67890',
        }
        response = self.client.post(self.url, data=form_data)

        # Check for the redirect
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('manage_venues'))

        # Verify the venue was updated
        self.venue.refresh_from_db()
        self.assertEqual(self.venue.name, 'Updated Venue')
        self.assertEqual(self.venue.address, '456 Updated St')
        self.assertEqual(self.venue.city, 'Updated City')
        self.assertEqual(self.venue.postcode, '67890')

        # Check for the success message
        messages = list(get_messages(response.wsgi_request))
        self.assertTrue(any('Venue updated successfully.' in str(m) for m in messages))

    def test_post_invalid_edit_venue_form(self):
        """Test that an invalid form submission does not update the venue."""
        self.client.login(username='manager', password='testpass')
        form_data = {
            'name': '',  # Invalid data (empty name)
            'address': '456 Updated St',
            'city': 'Updated City',
            'postcode': '67890',
        }
        response = self.client.post(self.url, data=form_data)

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'company/edit_venue.html')

        # Verify the venue was not updated
        self.venue.refresh_from_db()
        self.assertNotEqual(self.venue.name, '')  # Ensure the name was not updated to an empty string

        # Check for the error message
        self.assertContains(response, 'Form is invalid. Please correct the errors.')

    def test_edit_venue_not_in_company(self):
        """Test that a venue not belonging to the user's company cannot be edited."""
        other_company = Company.objects.create(name="Other Company", manager=self.manager_user)
        other_venue = Venue.objects.create(
            name="Other Venue",
            address="789 Other St",
            city="Other City",
            postcode="54321",
            company=other_company
        )

        self.client.login(username='manager', password='testpass')
        url = reverse('edit_venue', args=[other_venue.venue_id])
        response = self.client.get(url)

        self.assertRedirects(response, reverse('manage_venues'))

        # Check for the error message
        messages = list(get_messages(response.wsgi_request))
        self.assertTrue(any('Venue not found or does not belong to your company.' in str(m) for m in messages))


class ViewTokensViewTest(TestCase):
    def setUp(self):
        # Create a manager user and their company
        self.manager_user = User.objects.create_user(username='manager', password='testpass')
        self.company = Company.objects.create(name="Test Company", manager=self.manager_user)
        self.manager_user.profile.company = self.company
        self.manager_user.profile.save()

        # Create tokens for the manager
        self.token1 = Token.objects.create(user=self.manager_user, company=self.company, refunded=False, used=False)
        self.token2 = Token.objects.create(user=self.manager_user, company=self.company, refunded=True, used=False)

        # URL for the view tokens view
        self.url = reverse('view_tokens')

    def test_redirect_if_not_logged_in(self):
        """Test that unauthenticated users are redirected to the login page."""
        response = self.client.get(self.url)
        login_url = reverse('account_login')
        self.assertRedirects(response, f"{login_url}?next={self.url}")

    def test_view_tokens_with_tokens(self):
        """Test that the view displays tokens when they exist."""
        self.client.login(username='manager', password='testpass')

        # Replicate the annotation logic from the view
        tokens = Token.objects.filter(user=self.manager_user, company=self.company).annotate(
            refunded_priority=Case(
                When(refunded=False, then=1),
                When(refunded=True, then=2),
                default=3,
                output_field=IntegerField()
            )
        ).order_by('refunded_priority', '-purchased_on')

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'company/view_tokens.html')
        self.assertEqual(response.context['company'], self.company)
        self.assertQuerysetEqual(
            response.context['tokens'],
            tokens,
            transform=lambda x: x
        )
        self.assertContains(response, f'Found 2 tokens for your account.')

    def test_view_tokens_no_tokens(self):
        """Test that the view displays a message when no tokens exist."""
        Token.objects.filter(user=self.manager_user, company=self.company).delete()

        self.client.login(username='manager', password='testpass')
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'company/view_tokens.html')
        self.assertContains(response, 'No tokens found for your account.')


class PurchaseTokensViewTest(TestCase):
    def setUp(self):
        # Create a manager user and their company
        self.manager_user = User.objects.create_user(username='manager', password='testpass')
        self.company = Company.objects.create(name="Test Company", manager=self.manager_user)
        self.manager_user.profile.company = self.company
        self.manager_user.profile.token_count = 0
        self.manager_user.profile.save()

        # URL for the purchase tokens view
        self.url = reverse('purchase_tokens')

    def test_redirect_if_not_logged_in(self):
        """Test that unauthenticated users are redirected to the login page."""
        response = self.client.get(self.url)
        login_url = reverse('account_login')
        self.assertRedirects(response, f"{login_url}?next={self.url}")

    def test_get_purchase_tokens_form(self):
        """Test that the purchase tokens form is displayed for authenticated users."""
        self.client.login(username='manager', password='testpass')
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'company/purchase_tokens.html')
        self.assertIsInstance(response.context['form'], PurchaseTokenForm)

    def test_post_valid_purchase_tokens_form(self):
        """Test that a valid form submission purchases tokens."""
        self.client.login(username='manager', password='testpass')
        form_data = {'token_count': 5}
        response = self.client.post(self.url, data=form_data)

        # Check for the redirect
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('company_dashboard'))

        # Verify the tokens were created
        self.assertEqual(Token.objects.filter(user=self.manager_user, company=self.company).count(), 5)

        # Verify the token count in the user's profile
        self.manager_user.profile.refresh_from_db()
        self.assertEqual(self.manager_user.profile.token_count, 5)

        # Check for the success message
        messages = list(get_messages(response.wsgi_request))
        self.assertTrue(any('5 tokens purchased successfully.' in str(m) for m in messages))

    def test_post_invalid_purchase_tokens_form(self):
        """Test that an invalid form submission does not purchase tokens."""
        self.client.login(username='manager', password='testpass')
        form_data = {'token_count': 0}  # Invalid data (less than the minimum)
        response = self.client.post(self.url, data=form_data)

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'company/purchase_tokens.html')

        # Verify no tokens were created
        self.assertEqual(Token.objects.filter(user=self.manager_user, company=self.company).count(), 0)

        # Verify the token count in the user's profile remains unchanged
        self.manager_user.profile.refresh_from_db()
        self.assertEqual(self.manager_user.profile.token_count, 0)

        # Check for the correct error message
        self.assertContains(response, 'Ensure this value is greater than or equal to 1.')  # Update to match the actual error message

    def test_purchase_tokens_no_company(self):
        """Test that a user without a company cannot purchase tokens."""
        user_without_company = User.objects.create_user(username='nocompanyuser', password='testpass')
        user_without_company.profile.company = None  # Ensure the user has no company
        user_without_company.profile.save()

        self.client.login(username='nocompanyuser', password='testpass')
        response = self.client.post(self.url)  # Use POST to trigger the logic

        self.assertRedirects(response, reverse('company_dashboard'))
        messages = list(get_messages(response.wsgi_request))
        self.assertTrue(any('You do not have a company associated with your profile.' in str(m) for m in messages))


class RefundTokenViewTest(TestCase):
    def setUp(self):
        # Create a user and their company
        self.user = User.objects.create_user(username='testuser', password='testpass')
        self.company = Company.objects.create(name="Test Company", manager=self.user)
        self.user.profile.company = self.company
        self.user.profile.save()

        # Create a token for the user
        self.token = Token.objects.create(user=self.user, company=self.company, used=False, refunded=False)

        # URL for the refund token view
        self.url = reverse('refund_token', args=[self.token.id])

    def test_redirect_if_not_logged_in(self):
        """Test that unauthenticated users are redirected to the login page."""
        response = self.client.post(self.url)
        login_url = reverse('account_login')
        self.assertRedirects(response, f"{login_url}?next={self.url}")

    def test_refund_token_successfully(self):
        """Test that a token is marked for refund successfully."""
        self.client.login(username='testuser', password='testpass')
        response = self.client.post(self.url)

        # Check for the redirect
        self.assertRedirects(response, reverse('company_dashboard'))

        # Verify the token was updated
        self.token.refresh_from_db()
        self.assertTrue(self.token.used)
        self.assertTrue(self.token.refunded)

        # Verify the refund request was created
        refund_request = RefundRequest.objects.filter(user=self.user, token=self.token).first()
        self.assertIsNotNone(refund_request)
        self.assertEqual(refund_request.status, 'Pending')
        self.assertIsNone(refund_request.reviewed_by)

        # Check for the success message
        messages = list(get_messages(response.wsgi_request))
        self.assertTrue(any('Token marked for refund successfully and refund request has been sent' in str(m) for m in messages))

    def test_refund_token_invalid(self):
        """Test that an invalid token cannot be refunded."""
        self.client.login(username='testuser', password='testpass')

        # Use an invalid token ID
        invalid_url = reverse('refund_token', args=[999])  # Non-existent token ID
        response = self.client.post(invalid_url)

        # Check for the redirect
        self.assertRedirects(response, reverse('company_dashboard'))

        # Check for the error message
        messages = list(get_messages(response.wsgi_request))
        self.assertTrue(any('Token not found or is not eligible for refund.' in str(m) for m in messages))

    def test_refund_token_already_used_or_refunded(self):
        """Test that a token already used or refunded cannot be marked for refund."""
        self.client.login(username='testuser', password='testpass')

        # Mark the token as used and refunded
        self.token.used = True
        self.token.refunded = True
        self.token.save()

        response = self.client.post(self.url)

        # Check for the redirect
        self.assertRedirects(response, reverse('company_dashboard'))

        # Check for the error message
        messages = list(get_messages(response.wsgi_request))
        self.assertTrue(any('Token not found or is not eligible for refund.' in str(m) for m in messages))


class RefundClientTokenViewTest(TestCase):
    def setUp(self):
        # Create a manager user and their company
        self.manager_user = User.objects.create_user(username='manager', password='testpass')
        self.company = Company.objects.create(name="Test Company", manager=self.manager_user)
        self.manager_user.profile.company = self.company
        self.manager_user.profile.save()

        # Create a client user
        self.client_user = User.objects.create_user(username='client', password='testpass')
        self.client_user.profile.company = self.company
        self.client_user.profile.save()

        # Create a token for the client
        self.token = Token.objects.create(user=self.client_user, company=self.company, used=False, refunded=False)

        # URL for the refund client token view
        self.url = reverse('refund_client_token', args=[self.token.id])

    def test_redirect_if_not_logged_in(self):
        """Test that unauthenticated users are redirected to the login page."""
        response = self.client.post(self.url)
        login_url = reverse('account_login')
        self.assertRedirects(response, f"{login_url}?next={self.url}")

    def test_refund_client_token_successfully(self):
        """Test that a manager can refund a client's token successfully."""
        self.client.login(username='manager', password='testpass')
        response = self.client.post(self.url)

        # Check for the redirect
        self.assertRedirects(response, reverse('view_clients'))

        # Verify the token was updated
        self.token.refresh_from_db()
        self.assertTrue(self.token.used)
        self.assertTrue(self.token.refunded)

        # Verify the refund request was created or updated
        refund_request = RefundRequest.objects.filter(user=self.client_user, token=self.token).first()
        self.assertIsNotNone(refund_request)
        self.assertEqual(refund_request.status, 'Approved')
        self.assertEqual(refund_request.reviewed_by, self.manager_user)

        # Check for the success message
        messages = list(get_messages(response.wsgi_request))
        self.assertTrue(any('Token refund request approved successfully.' in str(m) for m in messages))

    def test_refund_client_token_no_permission(self):
        """Test that a manager cannot refund a token they do not have permission to refund."""
        other_company = Company.objects.create(name="Other Company", manager=self.manager_user)
        other_token = Token.objects.create(user=self.client_user, company=other_company, used=False, refunded=False)

        self.client.login(username='manager', password='testpass')
        url = reverse('refund_client_token', args=[other_token.id])
        response = self.client.post(url)

        # Check for the redirect
        self.assertRedirects(response, reverse('view_client_tokens', args=[self.client_user.id]))

        # Check for the error message
        messages = list(get_messages(response.wsgi_request))
        self.assertTrue(any('You do not have permission to refund this token.' in str(m) for m in messages))

    def test_refund_client_token_invalid(self):
        """Test that an invalid token cannot be refunded."""
        self.client.login(username='manager', password='testpass')

        # Use an invalid token ID
        invalid_url = reverse('refund_client_token', args=[999])  # Non-existent token ID
        response = self.client.post(invalid_url)

        # Check for the redirect
        self.assertRedirects(response, reverse('view_clients'))

        # Check for the error message
        messages = list(get_messages(response.wsgi_request))
        self.assertTrue(any('Token not found or is not eligible for refund.' in str(m) for m in messages))

    def test_refund_client_token_already_used_or_refunded(self):
        """Test that a token already used or refunded cannot be refunded again."""
        self.client.login(username='manager', password='testpass')

        # Mark the token as used and refunded
        self.token.used = True
        self.token.refunded = True
        self.token.save()

        response = self.client.post(self.url)

        # Check for the redirect
        self.assertRedirects(response, reverse('view_clients'))

        # Check for the error message
        messages = list(get_messages(response.wsgi_request))
        self.assertTrue(any('Token not found or is not eligible for refund.' in str(m) for m in messages))

class ViewRefundRequestsViewTest(TestCase):
    def setUp(self):
        # Create a manager user and their company
        self.manager_user = User.objects.create_user(username='manager', password='testpass')
        self.company = Company.objects.create(name="Test Company", manager=self.manager_user)
        self.manager_user.profile.company = self.company
        self.manager_user.profile.save()

        # Create a regular user (non-manager)
        self.regular_user = User.objects.create_user(username='regular', password='testpass')
        self.regular_user.profile.company = self.company
        self.regular_user.profile.save()

        # Create tokens and refund requests
        self.token1 = Token.objects.create(user=self.regular_user, company=self.company, used=True, refunded=True)
        self.token2 = Token.objects.create(user=self.regular_user, company=self.company, used=True, refunded=True)
        self.refund_request1 = RefundRequest.objects.create(user=self.regular_user, token=self.token1, status='Pending')
        self.refund_request2 = RefundRequest.objects.create(user=self.regular_user, token=self.token2, status='Approved')

        # URL for the view refund requests view
        self.url = reverse('view_refund_requests')

    def test_redirect_if_not_logged_in(self):
        """Test that unauthenticated users are redirected to the login page."""
        response = self.client.get(self.url)
        login_url = reverse('account_login')
        self.assertRedirects(response, f"{login_url}?next={self.url}")

    def test_manager_view_refund_requests(self):
        """Test that the manager can view all refund requests for their company."""
        self.client.login(username='manager', password='testpass')
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'company/view_refund_requests.html')
        self.assertEqual(response.context['company'], self.company)
        self.assertQuerysetEqual(
            response.context['refund_requests'],
            RefundRequest.objects.filter(token__company=self.company).annotate(
                status_priority=Case(
                    When(status='Pending', then=1),
                    When(status='Approved', then=2),
                    default=3,
                    output_field=IntegerField()
                )
            ).order_by('status_priority', '-created_at'),
            transform=lambda x: x
        )
        self.assertContains(response, f'Found 2 refund requests for your company.')

    def test_regular_user_view_refund_requests(self):
        """Test that a regular user can view their own refund requests."""
        self.client.login(username='regular', password='testpass')
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'company/view_refund_requests.html')
        self.assertEqual(response.context['company'], self.company)
        self.assertQuerysetEqual(
            response.context['refund_requests'],
            RefundRequest.objects.filter(user=self.regular_user).annotate(
                status_priority=Case(
                    When(status='Pending', then=1),
                    When(status='Approved', then=2),
                    default=3,
                    output_field=IntegerField()
                )
            ).order_by('status_priority', '-created_at'),
            transform=lambda x: x
        )
        self.assertContains(response, f'Found 2 refund requests for you.')

    def test_no_refund_requests(self):
        """Test that the view displays a message when no refund requests exist."""
        RefundRequest.objects.all().delete()

        self.client.login(username='manager', password='testpass')
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'company/view_refund_requests.html')
        self.assertContains(response, 'No refund requests found.')

    def test_user_without_company(self):
        """Test that a user without a company is redirected to the dashboard with an error message."""
        user_without_company = User.objects.create_user(username='nocompanyuser', password='testpass')
        self.client.login(username='nocompanyuser', password='testpass')

        response = self.client.get(self.url)

        self.assertRedirects(response, reverse('company_dashboard'))
        messages = list(get_messages(response.wsgi_request))
        self.assertTrue(any('You do not have a company associated with your profile.' in str(m) for m in messages))