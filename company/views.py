from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from .forms import CreateCompanyForm, ChangeCompanyDetailsForm, AddCoachForm, RemoveCoachForm, AddVenueForm, EditVenueForm, PurchaseTokenForm, JoinCompanyForm, TokenPriceUpdateForm
from booking.models import Booking, Event # Ensure Event is imported
from django.contrib import messages
from django.contrib.auth.models import User
from .models import Coach, Token, Venue, RefundRequest, TokenPurchase, Company, UserProfile, Image # Ensure all models are imported
from django.contrib.auth import get_user_model
from django.core.exceptions import ObjectDoesNotExist
from django.db.models import Case, When, IntegerField
from django.urls import reverse # Import reverse for dynamic URLs
import stripe
from django.conf import settings
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse, HttpResponseBadRequest, HttpResponse
import logging
from utils.email import send_custom_email

User = get_user_model() # Best practice for custom user model
logger = logging.getLogger(__name__) # Initialize logger


@login_required
def company_dashboard(request):
    try:
        if request.user.profile.company:
            company = request.user.profile.company
            # Check if the user is the manager
            if company.manager == request.user:
                return render(request, 'company/company_manager_dashboard.html', {'company': company})
            # Else if they are a coach or user (you can check for their role)
            else:
                tokens = Token.objects.filter(user=request.user, company=company, used=False).count()
                return render(request, 'company/company_user_dashboard.html', {'company': company,
                                                                               'user': request.user,
                                                                               'tokens': tokens})
        else:
            # If the user doesn't have a company, redirect to company creation page
            create_company_form = CreateCompanyForm(request.POST)
            join_company_form = JoinCompanyForm(request.POST)
            if request.method == 'POST':
                form = CreateCompanyForm(request.POST)
                if form.is_valid():
                    company = form.save(commit=False)
                    company.manager = request.user
                    company.save()

                    profile = request.user.profile  
                    profile.company = company
                    profile.save()

                    coach = Coach(coach=request.user, company=company)
                    coach.save()


                    messages.success(request, 'Company created successfully.')
                    return redirect('company_dashboard')  # update this to your URL name
            else:
                form = CreateCompanyForm()

            return render(request, 'company/create_company.html', {
                'create_form': create_company_form,
                'join_form': join_company_form,                                       
                })
    except User.profile.RelatedObjectDoesNotExist:
        messages.error(request, 'You do not have a profile associated with your account.')
        return redirect('home')
    
@login_required
def join_company(request):
    if request.method == 'POST':
        form = JoinCompanyForm(request.POST)
        if form.is_valid():
            if request.user.profile.company:
                return redirect('company_dashboard')
            company = form.cleaned_data['company']
            request.user.profile.company = company
            request.user.profile.save()
            messages.success(request, f'You have successfully joined the company: {company.name}.')
            return redirect('company_dashboard')
        else:
            messages.error(request, 'Form is invalid. Please correct the errors.')
    else:
        form = JoinCompanyForm()

    return redirect('company_dashboard')
    
@login_required
def change_company_details(request):
    if request.method == 'POST':
        form = ChangeCompanyDetailsForm(request.POST, instance=request.user.profile.company)
        if form.is_valid():
            form.save()
            messages.success(request, 'Company details updated successfully.')
            return redirect('company_dashboard')  # update this to your URL name
        else:
            messages.error(request, 'Form is not Valid')
    else:
        form = ChangeCompanyDetailsForm(instance=request.user.profile.company)

    return render(request, 'company/change_company_details.html', {'form': form,
                                                                   'company': request.user.profile.company})

@login_required
def view_coaches(request):
    # This function should be implemented to view coaches related to the company
    coaches = Coach.objects.filter(company=request.user.profile.company).order_by('coach__username')
    if not coaches:
        messages.info(request, 'No coaches found for your company.')
    else:
        messages.success(request, f'Found {coaches.count()} coaches for your company.')
    # Render the coaches in a template
    return render(request, 'company/view_coaches.html', {'company': request.user.profile.company,
                                                         'coaches': coaches})

@login_required
def add_coach(request):
    if request.method == 'POST':
        form = AddCoachForm(request.POST, user=request.user)
        if form.is_valid():
            company = request.user.profile.company
            if company:
                form.save(company)
                messages.success(request, 'Coach added successfully.')
                return redirect('company_dashboard')
    else:
        form = AddCoachForm(user=request.user)

    return render(request, 'company/add_coach.html', {'form': form,
                                                      'company': request.user.profile.company})

@login_required
def remove_coach(request):
    if request.method == 'POST':
        form = RemoveCoachForm(request.POST, user=request.user)
        if form.is_valid():
            coach = form.cleaned_data.get('coach')
            if coach:
                coach.delete()
                messages.success(request, f'Coach: {coach} removed successfully.')
                return redirect('company_dashboard')  # Correct redirect
            else:
                messages.error(request, 'Coach not found or does not belong to your company.')
                return redirect('company_dashboard')  # Correct redirect
    else:
        form = RemoveCoachForm(user=request.user)
    return render(request, 'company/remove_coach.html', {'form': form,
                                                          'company': request.user.profile.company})

@login_required
def view_clients(request):
    # This function should be implemented to view clients related to the company
    clients = User.objects.filter(profile__company=request.user.profile.company).exclude(id=request.user.id).exclude(id=request.user.profile.company.manager.id).exclude(id__in=Coach.objects.filter(company=request.user.profile.company).values_list('coach__id', flat=True)).order_by('username')
    if not clients:
        messages.info(request, 'No clients found for your company.')
    else:
        messages.success(request, f'Found {clients.count()} clients for your company.')
    # Render the clients in a template
    return render(request, 'company/view_clients.html', {'company': request.user.profile.company,
                                                         'clients': clients})

@login_required
def client_details(request, client_id):
    # This function should be implemented to view details of a specific client
    if request.method == 'POST':
        try:
            client = User.objects.get(id=client_id, profile__company=request.user.profile.company)
            return render(request, 'company/client_details.html', {'client': client,
                                                                   'company': request.user.profile.company})
        except User.DoesNotExist:
            messages.error(request, 'Client not found or does not belong to your company.')
            return redirect('view_clients')
    else:
        messages.error(request, 'Invalid request method.')
        return redirect('view_clients')

@login_required
def remove_client(request, client_id):
    if request.method == 'POST':
        try:
            client = User.objects.get(id=client_id, profile__company=request.user.profile.company)
            tokens = Token.objects.filter(user__id=client_id, company=request.user.profile.company, refunded=False, used=False)
            if tokens.exists():
                messages.error(request, 'Cannot remove client with active tokens. Please refund or use the tokens first.')
                return redirect('view_clients')
            if client.profile.company == request.user.profile.company and request.user.profile.company.manager == request.user:
                if Coach.objects.filter(coach=client, company=request.user.profile.company).exists():
                    messages.error(request, 'The selected client is also a coach and cannot be removed as a client.')
                    return redirect('view_clients')
                client.profile.company = None  # Remove the client from the company
                client.profile.save()
                messages.success(request, f'Client {client.username} removed successfully.')
                return redirect('view_clients')  # Redirect to the clients view after removal
            else:
                messages.error(request, 'You do not have permission to remove this client.')
                return redirect('company_dashboard')  # Redirect to the dashboard if permission denied
        except User.DoesNotExist:
            messages.error(request, 'Client not found or does not belong to your company.')
            return redirect('view_clients')

@login_required
def view_client_tokens(request, client_id):
    # This function should be implemented to view tokens related to a specific client
    try:
        client = User.objects.get(id=client_id, profile__company=request.user.profile.company)
        tokens = Token.objects.filter(user=client, company=request.user.profile.company).order_by('-purchased_on')
        if not tokens:
            messages.info(request, f'No tokens found for client {client.username}.')
        else:
            messages.success(request, f'Found {tokens.count()} tokens for client {client.username}.')
        # Render the tokens in a template
        return render(request, 'company/view_client_tokens.html', {'company': request.user.profile.company,
                                                                   'client': client,
                                                                   'tokens': tokens})
    except User.DoesNotExist:
        messages.error(request, 'Client not found or does not belong to your company.')
        return redirect('view_clients')

@login_required
def view_bookings(request):
    # This function should be implemented to view bookings related to the company
    bookings = Booking.objects.filter(event__coach__company=request.user.profile.company).order_by('-event__date_of_event')
    if not bookings:
        messages.info(request, 'No bookings found for your company.')
    else:
        messages.success(request, f'Found {bookings.count()} bookings for your company.')
    # Render the bookings in a template
    return render(request, 'company/view_bookings.html', {'company': request.user.profile.company,
                                                          'bookings': bookings})

@login_required
def delete_booking(request, booking):
    # This function should be implemented to delete a booking
    booking = Booking.objects.get(id=booking)
    if booking.event.coach.company == request.user.profile.company:
        messages.success(request, f'Booking:{booking.id} deleted successfully.')
        booking.delete()
    else:
        messages.error(request, 'You do not have permission to delete this booking.')
    return redirect('view_bookings')  # Redirect to the bookings view after deletion

@login_required
def manage_venues(request):
    try:
        venues = request.user.profile.company.venues.all()
        messages.success(request, f'Found {venues.count()} venues for your company.')
        return render(request, 'company/manage_venues.html', {'company': request.user.profile.company,
                                                                'venues': venues})
    except AttributeError:
        messages.error(request, 'You do not have a company associated with your profile.')
        return redirect('company_dashboard')

    
@login_required
def view_venue(request, venue_id):
    try:
        venue = Venue.objects.get(venue_id=venue_id, company=request.user.profile.company)
        return render(request, 'company/view_venue.html', {'venue': venue,
                                                           'company': request.user.profile.company})
    except Venue.DoesNotExist:
        messages.error(request, 'Venue not found or does not belong to your company.')
        return redirect('manage_venues')
    
@login_required
def add_venue(request):
    if not hasattr(request.user, 'profile') or not request.user.profile.company:
        messages.error(request, 'You do not have a company associated with your profile.')
        return redirect('company_dashboard')

    if request.method == 'POST':
        form = AddVenueForm(request.POST, user=request.user)  # Pass the user to the form
        if form.is_valid():
            venue = form.save(commit=False)
            venue.company = request.user.profile.company  # Associate the venue with the user's company
            venue.save()  # Save the venue to the database
            messages.success(request, 'Venue added successfully.')
            return redirect('manage_venues')
        else:
            messages.error(request, 'Form is invalid. Please correct the errors.')
    else:
        form = AddVenueForm(user=request.user)  # Pass the user to the form

    return render(request, 'company/add_venue.html', {'form': form,
                                                      'company': request.user.profile.company})

@login_required
def remove_venue(request, venue_id):
    try:
        # Fetch the venue for the user's company
        venue = Venue.objects.get(venue_id=venue_id, company=request.user.profile.company)

        # Count events and related bookings before deleting
        events = venue.event_venue.all()  # related_name from Event to Venue
        event_count = events.count()

        booking_count = sum(event.event_booking.count() for event in events)

        venue_name = venue.name
        venue.delete()  # This cascades to Events and Bookings

        messages.success(
            request,
            f'Venue "{venue_name}" removed. {event_count} events and {booking_count} bookings were deleted.'
        )

    except Venue.DoesNotExist:
        messages.error(request, 'Venue not found or does not belong to your company.')

    return redirect('manage_venues')


@login_required
def edit_venue(request, venue_id):
    try:
        # Use venue_id as the primary key and filter by the user's company
        venue = Venue.objects.get(venue_id=venue_id, company=request.user.profile.company)
        if request.method == 'POST':
            form = EditVenueForm(request.POST, venue_id=venue_id)  # Pass venue_id to the form
            if form.is_valid():
                form.save()  # Save the updated venue
                messages.success(request, 'Venue updated successfully.')
                return redirect('manage_venues')
            else:
                messages.error(request, 'Form is invalid. Please correct the errors.')
        else:
            form = EditVenueForm(venue_id=venue_id)  # Pass venue_id to the form
        return render(request, 'company/edit_venue.html', {'form': form,
                                                           'company': request.user.profile.company,
                                                           'venue': venue})
    except Venue.DoesNotExist:
        messages.error(request, 'Venue not found or does not belong to your company.')
        return redirect('manage_venues')  # Redirect to the venues management view if venue not found


# Tokens and purchases
@login_required
def view_tokens(request):
    # This function should be implemented to view tokens related to the company
    tokens = Token.objects.filter(user=request.user, company=request.user.profile.company).annotate(
        refunded_priority=Case(
            When(refunded=False, then=1),
            When(refunded=True, then=2),
            default=3,
            output_field=IntegerField()
        )
    ).order_by('refunded_priority', '-purchased_on')
    if not tokens:
        messages.info(request, 'No tokens found for your account.')
    else:
        messages.success(request, f'Found {tokens.count()} tokens for your account.')
    # Render the tokens in a template
    return render(request, 'company/view_tokens.html', {'company': request.user.profile.company,
                                                        'tokens': tokens})

@login_required
def purchase_tokens(request):
    if request.method == 'POST':
        if not request.user.profile.company:
            messages.error(request, 'You do not have a company associated with your profile.')
            return redirect('company_dashboard')
        form = PurchaseTokenForm(request.POST, user=request.user)  # Pass the user to the form
        if form.is_valid():
            token_count = form.cleaned_data['token_count']
            company = request.user.profile.company
            if company:
                # create token purchase object
                total_price = token_count * company.token_price
                purchase = TokenPurchase.objects.create(
                    user = request.user,
                    company=company,
                    tokens_bought=token_count,
                    total_price=total_price
                )
                # Create tokens for the user
                for _ in range(token_count):
                    Token.objects.create(user=request.user, company=company, purchase=purchase)
                request.user.profile.token_count += token_count
                request.user.profile.save()
                messages.success(request, f'{token_count} tokens purchased successfully.')
                return redirect('company_dashboard')
            else:
                messages.error(request, 'You do not have a company associated with your profile.')
    else:
        form = PurchaseTokenForm(user=request.user)  # Pass the user to the form

    return render(request, 'company/purchase_tokens.html', {'form': form,
                                                            'company': request.user.profile.company})


@login_required
def refund_token(request, token_id):
    if request.method == 'POST':
        try:
            token = Token.objects.get(user=request.user, used=False, refunded=False, id=token_id)
            token.used = True
            token.refunded = True
            token.save()
            # Create a refund request
            refund_request = RefundRequest.objects.create(
                user=request.user,
                token=token,
                status='Pending',
                reviewed_by=None  # Initially, no one has reviewed it
            )
            admin_email = refund_request.token.company.manager.email  # Adjust if needed

            send_custom_email(
                subject="New Refund Request Submitted",
                message=f"A refund request was submitted by {request.user.username}.",
                recipient_list=[admin_email]
            )

            messages.success(request, 'Token marked for refund successfully and refund request has been sent')
        except Token.DoesNotExist:
            messages.error(request, 'Token not found or is not eligible for refund.')
    return redirect('company_dashboard')


@login_required
def view_refund_requests(request):
    if not hasattr(request.user, 'profile') or not request.user.profile.company:
        messages.error(request, 'You do not have a company associated with your profile.')
        return redirect('company_dashboard')

    company = request.user.profile.company
    is_manager = (company.manager == request.user)

    if is_manager:
        refund_requests = RefundRequest.objects.filter(token__company=company)
    else:
        refund_requests = RefundRequest.objects.filter(user=request.user)

    refund_requests = refund_requests.annotate(
        status_priority=Case(
            When(status='Pending', then=1),
            When(status='Approved', then=2),
            default=3,
            output_field=IntegerField()
        )
    ).order_by('status_priority', '-created_at')

    if refund_requests.exists():
        if is_manager:
            messages.success(request, f'Found {refund_requests.count()} refund requests for your company.')
        else:
            messages.success(request, f'Found {refund_requests.count()} refund requests for you.')
    else:
        messages.info(request, 'No refund requests found.')

    return render(request, 'company/view_refund_requests.html', {
        'refund_requests': refund_requests,
        'company': company
    })



@login_required
def deny_refund_request(request, request_id):
    try:
        refund_request = RefundRequest.objects.get(id=request_id, token__company=request.user.profile.company)
        refund_request.status = 'Denied'
        refund_request.reviewed_by = request.user
        try:
            if not refund_request.token:
                raise Token.DoesNotExist  # Explicitly raise the exception if the token is missing
            refund_request.token.used = False  # Mark the token as used
            refund_request.token.refunded = False  # Mark the token as refunded
            refund_request.token.save()
            send_custom_email(
            subject="Your Refund Request Has Been Denied",
            message="Unfortunately, your refund request has been denied and the tokens have been returned to you. Please contact your gym for more info.",
            recipient_list=[refund_request.user.email]
        )

        except Token.DoesNotExist:
            messages.error(request, 'Token associated with this refund request does not exist.')
            return redirect('view_refund_requests')
        refund_request.save()
        messages.success(request, 'Refund request denied successfully. Token returned to client')
    except RefundRequest.DoesNotExist:
        messages.error(request, 'Refund request not found or does not belong to your company.')

    return redirect('view_refund_requests')

@login_required
def client_leave_company(request):
    try:
        # Check if the user has a valid company in their profile
        if not request.user.profile.company:
            messages.error(request, 'You are not associated with any company.')
            return redirect('company_dashboard')

        # Check if the user has any unused and unrefunded tokens
        unused_tokens = Token.objects.filter(user=request.user, company=request.user.profile.company, used=False, refunded=False)
        if unused_tokens.exists():
            messages.error(request, 'You cannot leave the company while you have unused or unrefunded tokens.')
            return redirect('company_dashboard')

        # Remove the user's company association
        request.user.profile.company = None
        request.user.profile.save()

        messages.success(request, 'You have successfully left the company.')
        return redirect('company_dashboard')

    except AttributeError:
        messages.error(request, 'An error occurred while processing your request.')
        return redirect('home')

@login_required
def update_token_price(request):
    company = request.user.profile.company

    # You could also check here if user is a manager
    if not request.user == company.manager:
        messages.error(request, 'You do not have permission to update the token price.')
        return redirect('dashboard')  # or show an error

    if request.method == "POST":
        form = TokenPriceUpdateForm(request.POST, instance=company)
        if form.is_valid():
            form.save()
            messages.success(request, 'Token price updated successfully.')
            return redirect("company_dashboard")  # wherever you want
    else:
        form = TokenPriceUpdateForm(instance=company)

    return render(request, "company/update_token_price.html", {
        "form": form,
        "company": company
    })


# stripe


stripe.api_key = settings.STRIPE_SECRET_KEY



# --- Stripe Connect Onboarding Views (MODIFIED FOR COMPANY) ---
# These views handle the process of a company manager connecting their company's Stripe account.
@login_required
def stripe_onboard_company(request):
    """
    Initiates the Stripe Connect onboarding process for a company.
    Only the company manager can access this view.
    It creates a new Stripe Express account for the company if one doesn't exist,
    then generates an AccountLink to redirect the manager to Stripe's hosted onboarding flow.
    """
    # Authorization check: Ensure user has a company and is its manager
    if not hasattr(request.user, 'profile') or not request.user.profile.company:
        messages.error(request, 'You do not have a company associated with your profile.')
        return redirect('company_dashboard')

    company = request.user.profile.company
    if company.manager != request.user:
        messages.error(request, 'You are not authorized to manage Stripe onboarding for this company.')
        return redirect('company_dashboard')

    try:
        # Check if the company already has a Stripe account ID
        if not company.stripe_account_id:
            # If not, create a new Stripe Express account
            account = stripe.Account.create(
                type='express', # Express accounts are suitable for platforms
                country='GB', # Set the country for the connected account (e.g., Great Britain)
                email=company.email, # Use the company's email for the Stripe account
                capabilities={
                    'card_payments': {'requested': True}, # Enable card payment processing
                    'transfers': {'requested': True},     # Enable money transfers (payouts)
                },
                # --- MODIFIED: Changed business_type to 'individual' ---
                business_type='individual', # This is for personal trainers, sole proprietors, small unincorporated gyms
                # Removed the 'company' dictionary as it's not applicable for 'individual' business_type
                # Stripe's hosted onboarding will collect the individual's legal name, DOB, address, etc.
                # --------------------------------------------------------
            )
            company.stripe_account_id = account.id # Save the new Stripe account ID to your Company model
            company.save()
            logger.info(f"New Stripe Express account created for Company {company.name}: {account.id} (business_type: individual)")
            messages.info(request, "New Stripe account created for your company. Redirecting to onboarding...")
        else:
            # If a Stripe account ID already exists, retrieve it to ensure it's valid
            account = stripe.Account.retrieve(company.stripe_account_id)
            logger.info(f"Existing Stripe Express account retrieved for Company {company.name}: {account.id} (business_type: {account.business_type})")
            messages.info(request, "Existing Stripe account found. Redirecting to complete onboarding...")

        # Create an AccountLink to redirect the company manager to Stripe's hosted onboarding flow
        account_link = stripe.AccountLink.create(
            account=company.stripe_account_id,
            # URLs Stripe will redirect back to after onboarding or if the link expires
            refresh_url=request.build_absolute_uri(reverse('stripe_onboard_company_refresh')), # Removed 'company:'
            return_url=request.build_absolute_uri(reverse('stripe_onboard_company_return')), # Removed 'company:'
            type='account_onboarding', # Specifies the purpose of the link
            collect='eventually_due', # Tells Stripe to collect all required info eventually
        )
        return redirect(account_link.url) # Redirect the user to Stripe's onboarding URL

    except stripe.error.StripeError as e:
        # Handle Stripe-specific API errors
        messages.error(request, f"Stripe error during company onboarding: {e.user_message}")
        logger.error(f"Stripe error during company onboarding for {company.name}: {e}", exc_info=True)
        return redirect('company_dashboard') # Redirect to a safe page on error
    except Exception as e:
        # Handle any other unexpected errors
        messages.error(request, f"An unexpected error occurred during company onboarding: {e}")
        logger.critical(f"Unexpected error during company onboarding for {company.name}: {e}", exc_info=True)
        return redirect('company_dashboard')



@login_required
def stripe_onboard_company_return(request):
    """
    Handles the return from Stripe's hosted onboarding flow for a company.
    Checks the status of the connected account and updates the company's onboarding status.
    """
    # Authorization check
    if not hasattr(request.user, 'profile') or not request.user.profile.company:
        messages.error(request, 'You do not have a company associated with your profile.')
        return redirect('company_dashboard')

    company = request.user.profile.company
    if company.manager != request.user:
        messages.error(request, 'You are not authorized to manage Stripe onboarding for this company.')
        return redirect('company_dashboard')

    try:
        # Ensure a Stripe account ID exists for the company
        if not company.stripe_account_id:
            messages.error(request, "No Stripe account ID found for your company.")
            return redirect('company_dashboard')

        # Retrieve the Stripe account details to check its status
        account = stripe.Account.retrieve(company.stripe_account_id)
        if account.details_submitted:
            # If details are submitted, mark onboarding as complete in your database
            company.stripe_onboarding_completed = True
            company.save()
            messages.success(request, f"Stripe onboarding for {company.name} completed successfully!")
            logger.info(f"Stripe onboarding completed for Company {company.name}.")
            return redirect('company_dashboard') # Redirect to company manager dashboard
        else:
            # If details are not yet submitted, inform the user and prompt to continue
            messages.warning(request, f"Stripe onboarding for {company.name} is not yet complete. Please continue the process.")
            logger.warning(f"Stripe onboarding for Company {company.name} not complete upon return.")
            # Redirect back to initiate onboarding to generate a new link
            return redirect(reverse('stripe_onboard_company'))

    except stripe.error.StripeError as e:
        messages.error(request, f"Stripe error during company onboarding return: {e.user_message}")
        logger.error(f"Stripe error during company onboarding return for {company.name}: {e}", exc_info=True)
        return redirect('company_dashboard')
    except Exception as e:
        messages.error(request, f"An unexpected error occurred during company onboarding return: {e}")
        logger.critical(f"Unexpected error during company onboarding return for {company.name}: {e}", exc_info=True)
        return redirect('company_dashboard')


@login_required
def stripe_onboard_company_refresh(request):
    """
    Handles the refresh URL for Stripe onboarding.
    Simply redirects back to the onboarding initiation view to generate a new AccountLink.
    """
    messages.info(request, "Redirecting to continue Stripe onboarding for your company.")
    logger.info(f"Stripe onboarding refresh requested for Company.")
    return redirect(reverse('stripe_onboard_company'))


# --- Stripe Checkout for Token Purchases (MODIFIED FOR CONNECT) ---
# This view initiates the Stripe Checkout session for buying tokens.
# The actual TokenPurchase and Token creation will happen in the webhook.
@login_required
def create_checkout_session(request):
    """
    Creates a Stripe Checkout Session for purchasing tokens.
    Funds for token purchases are directed to the Company's Stripe Connect account,
    with a fixed 25p application fee going to the platform.
    """
    if request.method == 'POST':
        try:
            company = request.user.profile.company
            if not company:
                messages.error(request, 'You must be part of a company to purchase tokens.')
                return redirect('company_dashboard')

            # Crucial: Ensure the company's Stripe account is onboarded before accepting payments for them
            if not company.stripe_account_id or not company.stripe_onboarding_completed:
                messages.error(request, "The company's Stripe account is not fully set up to receive payments. Please contact the company manager.")
                # Redirect back to the purchase page so they can see the error
                return redirect(reverse('purchase_tokens'))

            token_count = int(request.POST.get('token_count'))
            if token_count <= 0:
                messages.error(request, 'Token count must be a positive number.')
                return redirect(reverse('purchase_tokens'))

            unit_price = company.token_price # This is the full price per token (e.g., £2.00)
            # Calculate the total amount to be charged to the customer in Stripe's smallest unit (pence)
            total_amount_in_cents = int(unit_price * token_count * 100)

            # Define your platform's fixed fee (25p per transaction)
            platform_fixed_fee_in_pence = 25 # 25 pence
            application_fee_amount = platform_fixed_fee_in_pence

            # Safeguard: Ensure the application fee does not exceed the total amount charged
            if application_fee_amount >= total_amount_in_cents:
                messages.error(request, "The platform fee is too high for this transaction. Please adjust token count or price.")
                logger.error(f"Application fee ({application_fee_amount}) exceeds total amount ({total_amount_in_cents}) for token purchase by user {request.user.id}.")
                return redirect(reverse('purchase_tokens'))


            # Dynamically generate success and cancel URLs using reverse
            success_url = request.build_absolute_uri(reverse('checkout_success'))
            cancel_url = request.build_absolute_uri(reverse('checkout_cancel'))

            # Create the Stripe Checkout Session
            session = stripe.checkout.Session.create(
                payment_method_types=['card'], # Specify accepted payment methods
                line_items=[{
                    'price_data': {
                        'currency': 'gbp', # Currency of the transaction
                        'product_data': {
                            'name': f'{token_count} Tokens for {company.name}',
                            'description': f'Purchase of {token_count} tokens for ClassifyBooking (Company: {company.name}).',
                        },
                        'unit_amount': int(unit_price * 100), # Full unit price in pence
                    },
                    'quantity': token_count,
                }],
                mode='payment', # Use 'payment' for one-time purchases
                # --- KEY CONNECT PARAMETERS within payment_intent_data ---
                # This block configures how the underlying PaymentIntent (created by Checkout)
                # will handle the funds.
                payment_intent_data={
                    'application_fee_amount': application_fee_amount, # Your platform's fixed 25p fee
                    'transfer_data': {
                        'destination': company.stripe_account_id, # The ID of the connected company's Stripe account
                    },
                    'description': f'Purchase of {token_count} tokens for company {company.name}',
                },
                # --------------------------------------------------------
                metadata={ # Custom data passed to Stripe, useful for webhooks
                    'user_id': str(request.user.id),
                    'token_count': str(token_count),
                    'company_id': str(company.company_id),
                    'purchase_type': 'token_purchase', # Helps identify this transaction type in webhooks
                },
                success_url=success_url,
                cancel_url=cancel_url,
            )
            logger.info(f"Stripe Checkout Session created: {session.id} for user {request.user.id}, destined for company {company.name} ({company.stripe_account_id}) with fee {application_fee_amount}p.")
            return redirect(session.url, code=303) # Redirect the user to Stripe's hosted Checkout page
        except stripe.error.StripeError as e:
            # Handle Stripe API errors during session creation
            messages.error(request, f"Stripe error creating checkout session: {e.user_message}")
            logger.error(f"Stripe error creating checkout session for user {request.user.id}: {e}", exc_info=True)
            return redirect(reverse('purchase_tokens'))
        except Exception as e:
            # Handle any other unexpected errors
            messages.error(request, f"An unexpected error occurred: {e}")
            logger.critical(f"Unexpected error creating checkout session for user {request.user.id}: {e}", exc_info=True)
            return redirect(reverse('purchase_tokens'))

# --- Success and Cancel views (These remain unchanged) ---
def success_view(request):
    messages.success(request, "Payment successful! Your tokens will be added to your account shortly.")
    return render(request, "company/success.html")

def cancel_view(request):
    messages.info(request, "Payment cancelled. No tokens were purchased.")
    return render(request, "company/cancel.html")

# --- Refund views (These remain largely unchanged, but rely on the stripe_payment_intent_id from TokenPurchase) ---
# Ensure your TokenPurchase model has stripe_payment_intent_id field.
@login_required
def refund_client_token(request, token_id):
    """
    Handles the refund of a single token via Stripe.
    This is initiated by the company manager.
    """
    if request.method == 'POST':
        try:
            token = Token.objects.get(id=token_id, used=False, refunded=False)
            token_company = token.company

            # Authorization check: Ensure logged-in user is the manager of the token's company
            if token_company.manager != request.user:
                messages.error(request, 'You do not have permission to refund this token.')
                return redirect('view_client_tokens', client_id=token.user.id)

            # Ensure the token is linked to a purchase and has a Stripe payment_intent_id
            if not token.purchase or not token.purchase.stripe_payment_intent_id:
                messages.error(request, 'Token does not have a valid payment intent for refund.')
                return redirect('view_client_tokens', client_id=token.user.id)

            purchase = token.purchase
            payment_intent_id = purchase.stripe_payment_intent_id

            # Calculate cost per token in Stripe's smallest unit (pence)
            # This is the amount that was originally paid for one token
            cost_per_token = int(purchase.get_cost_per_token() * 100)

            # Perform the Stripe refund for the amount of one token
            refund = stripe.Refund.create(
                payment_intent=payment_intent_id,
                amount=cost_per_token, # Refund only the cost of one token
                metadata={ # Custom metadata for your records in Stripe
                    "refunded_user": token.user.get_full_name() or token.user.username,
                    "refunded_user_id": token.user.id,
                    "refunded_by": request.user.get_full_name() or request.user.username,
                    "token_id": token.id
                }
            )
            # Mark token as used and refunded in your database
            token.used = True
            token.refunded = True
            token.save()

            # Update associated refund request status if it exists
            refund_request = RefundRequest.objects.filter(token=token, user=token.user, status='Pending').first()
            if refund_request:
                refund_request.status = 'Approved'
                refund_request.reviewed_by = request.user
                refund_request.save()
                messages.success(request, 'Stripe refund issued and request marked approved.')
            else:
                # Create a new refund request if one didn't exist (e.g., direct refund by manager)
                RefundRequest.objects.create(
                    user=token.user,
                    token=token,
                    status='Approved',
                    reviewed_by=request.user
                )
                messages.success(request, 'Token refunded via Stripe successfully.')

            # Send confirmation email to the user
            send_custom_email(
                subject="Token Refund Confirmation",
                message=f"Dear {token.user.username},\n\nYour token with ID {token.id} has been successfully refunded by {request.user.username}. Refund value: £{cost_per_token / 100:.2f}. If you have any questions, please contact your gym.\n\nBest regards,\nClassifyBooking Team",
                recipient_list=[token.user.email]
            )

        except Token.DoesNotExist:
            messages.error(request, 'Token not found or is not eligible for refund.')
        except stripe.error.StripeError as e:
            messages.error(request, f'Stripe error: {str(e.user_message or e)}')
        except Exception as e:
            messages.error(request, f'Unexpected error: {str(e)}')

    return redirect('view_clients')

@login_required
def approve_refund_request(request, request_id):
    """
    Approves a pending refund request and initiates a Stripe refund.
    Only the company manager can access this view.
    """
    # Authorization check
    if not hasattr(request.user, 'profile') or not request.user.profile.company:
        messages.error(request, 'You do not have a company associated with your profile.')
        return redirect('company_dashboard')
    if request.user.profile.company.manager != request.user:
        messages.error(request, 'You are not authorized to approve refund requests.')
        return redirect('company_dashboard')

    try:
        refund_request = RefundRequest.objects.get(
            id=request_id,
            token__company=request.user.profile.company,
            status='Pending' # Ensure only pending requests can be approved
        )
        token = refund_request.token
        purchase = token.purchase

        if not purchase:
            messages.error(request, 'Token is not eligible for refund (no associated purchase).')
            return redirect('view_refund_requests')

        if not purchase.stripe_payment_intent_id:
            messages.error(request, 'Token purchase has no associated Stripe PaymentIntent ID for refund.')
            return redirect('view_refund_requests')

        cost_per_token = purchase.get_cost_per_token()
        amount_to_refund = int(cost_per_token * 100) # Amount in pence

        # Perform the Stripe refund
        refund = stripe.Refund.create(
            payment_intent=purchase.stripe_payment_intent_id,
            amount=amount_to_refund,
            metadata={
                "refunded_user": token.user.get_full_name() or token.user.username,
                "refunded_user_id": token.user.id,
                "refunded_by": request.user.get_full_name() or request.user.username,
                "reviewer_user_id": request.user.id,
                "token_id": token.id
            }
        )

        # Update token and refund request status in your database
        token.refunded = True
        token.used = True # Mark as used so it can't be used again
        token.save()

        refund_request.status = 'Approved'
        refund_request.reviewed_by = request.user
        refund_request.save()

        # Send confirmation email to the user
        send_custom_email(
            subject="Token Refund Confirmation",
            message=f"Dear {token.user.username},\n\nYour token with ID {token.id} has been successfully refunded by {request.user.username}. Refund value: £{cost_per_token:.2f}. If you have any questions, please contact your gym.\n\nBest regards,\nClassifyBooking Team",
            recipient_list=[token.user.email]
        )

        messages.success(request, f'Token refunded and request approved. Stripe Refund ID: {refund.id}')
    except RefundRequest.DoesNotExist:
        messages.error(request, 'Refund request not found or does not belong to your company.')
    except stripe.error.StripeError as e:
        messages.error(request, f'Stripe error: {str(e.user_message or e)}')
    except Exception as e:
        messages.error(request, f'Unexpected error: {str(e)}')

    return redirect('view_refund_requests')

# --- Stripe Webhook (No changes needed here for the money flow, as Stripe handles the transfer) ---
# The existing checkout.session.completed handler will correctly process the metadata
# and create the TokenPurchase and Token objects.
# The `session.get('payment_intent')` will still give you the ID of the PaymentIntent
# that facilitated the transfer and fee.
@csrf_exempt
def stripe_webhook(request):
    """
    Handles incoming Stripe webhook events.
    Verifies the webhook signature and processes different event types,
    such as `checkout.session.completed` for token purchases and `account.updated`
    for company onboarding status.
    """
    try:
        logger.info(f"Webhook received! Method: {request.method}, Path: {request.path}")

        payload = request.body
        sig_header = request.META.get('HTTP_STRIPE_SIGNATURE')
        endpoint_secret = settings.STRIPE_WEBHOOK_SECRET # Your webhook secret from settings.py

        logger.info(f"Signature Header: {sig_header}")
        logger.info(f"Endpoint Secret (first 5 chars): {endpoint_secret[:5]}...")

        if not sig_header:
            logger.error("Missing Stripe signature header.")
            return HttpResponseBadRequest("Missing Stripe signature header.")

        try:
            # Construct the event from the payload, header, and secret for verification
            event = stripe.Webhook.construct_event(payload, sig_header, endpoint_secret)
            logger.info(f"Stripe event constructed successfully. Type: {event['type']}")
        except (ValueError, stripe.error.SignatureVerificationError) as e:
            # Invalid payload or signature
            logger.error(f"Stripe webhook signature verification error: {e}", exc_info=True)
            return HttpResponseBadRequest(f"Webhook signature verification failed: {e}")
        except Exception as e:
            # Catch any other unexpected errors during event construction
            logger.error(f"Unexpected error during webhook construction: {e}", exc_info=True)
            return HttpResponseBadRequest(f"Unexpected error: {e}")

        # Handle the event based on its type
        if event['type'] == 'checkout.session.completed':
            # This event signifies a successful Stripe Checkout Session
            session = event['data']['object']
            logger.info(f"Checkout Session Completed: {session['id']}, Payment Status: {session.get('payment_status')}")

            # Ensure the payment was actually successful before processing
            if session.get("payment_status") != "paid":
                logger.warning(f"Payment status is not 'paid' for session {session['id']}. Status: {session.get('payment_status')}. Returning 200.")
                return HttpResponse(status=200) # Acknowledge webhook but don't process if not paid

            # Extract metadata that you passed during session creation
            metadata = session.get('metadata', {})
            user_id = metadata.get('user_id')
            token_count_str = metadata.get('token_count')
            company_id = metadata.get('company_id')
            purchase_type = metadata.get('purchase_type') # Expected to be 'token_purchase'

            logger.info(f"Extracted Metadata: user_id={user_id}, token_count_str={token_count_str}, company_id={company_id}, purchase_type={purchase_type}")

            # Validate critical metadata is present
            if not all([user_id, token_count_str, company_id, purchase_type]):
                logger.error(f"Missing required metadata in checkout.session.completed event for session {session['id']}.")
                return HttpResponseBadRequest("Missing required metadata.")

            # Process only if it's a token purchase (as identified by metadata)
            if purchase_type == 'token_purchase':
                try:
                    token_count = int(token_count_str)
                    user = User.objects.get(id=user_id)
                    company = Company.objects.get(company_id=company_id)
                    logger.info(f"User and Company found: {user.username}, {company.name}")

                    # `session['amount_total']` is the total amount the customer paid (in cents)
                    total_price_in_currency_units = session['amount_total'] / 100.0

                    # Create the TokenPurchase record in your database
                    purchase = TokenPurchase.objects.create(
                        user=user,
                        company=company,
                        tokens_bought=token_count,
                        total_price=total_price_in_currency_units,
                        # Store the PaymentIntent ID for potential refunds later
                        stripe_payment_intent_id=session.get('payment_intent')
                    )
                    logger.info(f"TokenPurchase created: {purchase.id} for user {user.username}.")

                    # Create individual Token objects
                    tokens_to_create = [
                        Token(user=user, company=company, purchase=purchase)
                        for _ in range(token_count)
                    ]
                    Token.objects.bulk_create(tokens_to_create)
                    logger.info(f"{token_count} Tokens created for user {user.username}.")

                    # Update the user's profile token count
                    user_profile, created = UserProfile.objects.get_or_create(user=user)
                    user_profile.token_count += token_count
                    user_profile.save()
                    logger.info(f"UserProfile token_count updated for {user.username}. New count: {user_profile.token_count}")

                    # Send confirmation email
                    send_custom_email(
                        subject="Token Purchase Confirmation",
                        message=f"Dear {user.username},\n\nYou have successfully purchased {token_count} tokens for {company.name}. Total price: £{total_price_in_currency_units:.2f}. Thank you for your purchase!\n\nBest regards,\nClassifyBooking Team",
                        recipient_list=[user.email]
                    )
                    logger.info(f"Confirmation email sent to {user.email}.")

                except (User.DoesNotExist, Company.DoesNotExist) as e:
                    logger.error(f"User or Company not found for checkout.session.completed event (session {session['id']}): {e}", exc_info=True)
                    return HttpResponseBadRequest(f"User or Company not found: {e}")
                except Exception as e:
                    logger.critical(f"Error processing checkout.session.completed event for session {session['id']}: {e}", exc_info=True)
                    return HttpResponseBadRequest(f"Error processing webhook: {e}")
            else:
                logger.warning(f"Unhandled purchase_type '{purchase_type}' in checkout.session.completed event for session {session['id']}.")


        elif event['type'] == 'account.updated':
            # This webhook handles updates to the *Company's* Stripe Connect account.
            # It keeps your database's onboarding status in sync with Stripe.
            account = event['data']['object']
            logger.info(f"Stripe Account updated: {account['id']}")
            try:
                # Find the Company by its Stripe account ID
                company = Company.objects.get(stripe_account_id=account['id'])
                if account['details_submitted'] and not company.stripe_onboarding_completed:
                    # If details are now submitted and it wasn't marked complete before
                    company.stripe_onboarding_completed = True
                    company.save()
                    logger.info(f"Company {company.name} ({company.company_id}) onboarding marked complete via webhook.")
                elif not account['details_submitted'] and company.stripe_onboarding_completed:
                    # If details are no longer submitted (e.g., Stripe requires more info)
                    company.stripe_onboarding_completed = False
                    company.save()
                    logger.warning(f"Company {company.name} ({company.company_id}) onboarding marked incomplete via webhook (details_submitted is false).")
            except Company.DoesNotExist:
                logger.warning(f"Company with Stripe account ID {account['id']} not found for account.updated event.")

        elif event['type'] == 'payment_intent.succeeded':
            # This block is intended for payments where funds are transferred to the Company's Stripe account,
            # such as booking payments (which you would implement separately).
            payment_intent = event['data']['object']
            logger.info(f"PaymentIntent succeeded: {payment_intent['id']}")
            booking_id = payment_intent['metadata'].get('booking_id') # Assumes 'booking_id' metadata is set
            if booking_id:
                try:
                    booking = Booking.objects.get(id=booking_id)
                    booking.status = 0 # Example: Update booking status to 'Confirmed'
                    booking.save()
                    logger.info(f"Booking {booking_id} confirmed via webhook for PaymentIntent {payment_intent['id']}.")
                except Booking.DoesNotExist:
                    logger.error(f"Booking {booking_id} not found for PaymentIntent {payment_intent['id']}.")
            else:
                logger.warning(f"PaymentIntent {payment_intent['id']} succeeded but no booking_id in metadata. This might be a direct payment not related to a specific booking in your system.")

        # Add more event types as needed (e.g., payout.paid, charge.refunded, etc.)
        # For a full list of events: https://stripe.com/docs/api/events/types

    except Exception as e:
        logger.critical(f"CRITICAL: Unhandled exception in Stripe webhook: {e}", exc_info=True)
        return HttpResponseBadRequest(f"An unexpected error occurred: {e}")

    return HttpResponse(status=200) # Always return 200 for successful webhook receipt
