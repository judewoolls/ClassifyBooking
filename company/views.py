from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from .forms import CreateCompanyForm, ChangeCompanyDetailsForm, AddCoachForm, RemoveCoachForm, AddVenueForm, EditVenueForm, PurchaseTokenForm, JoinCompanyForm, TokenPriceUpdateForm
from booking.models import Booking
from django.contrib import messages
from django.contrib.auth.models import User
from .models import Coach, Token, Venue, RefundRequest, TokenPurchase, Company, UserProfile
from django.contrib.auth import get_user_model
from django.shortcuts import get_object_or_404
from django.core.exceptions import ObjectDoesNotExist
from django.db.models import Case, When, IntegerField
import stripe
from django.conf import settings
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse, HttpResponseBadRequest, HttpResponse
import logging
from utils.email import send_custom_email

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

# purchasing tokens
@login_required
def create_checkout_session(request):
    if request.method == 'POST':
        try:
            company = request.user.profile.company
            token_count = int(request.POST.get('token_count'))
            unit_price = company.token_price  # price per token in pence (e.g. £2.00)
            total_price = token_count * unit_price

            session = stripe.checkout.Session.create(
                payment_method_types=['card'],
                line_items=[{
                    'price_data': {
                        'currency': 'gbp',
                        'product_data': {
                            'name': f'{token_count} Tokens',
                        },
                        'unit_amount': int(unit_price) * 100,  # price in pence
                    },
                    'quantity': token_count,
                }],
                mode='payment',
                payment_intent_data={
                    'description': f'Purchase of {token_count} tokens for company {company.name}',
                },
                success_url='http://classifybooking-2be97a09d742.herokuapp.com/company/checkout/success/',
                cancel_url='http://classifybooking-2be97a09d742.herokuapp.com/company/checkout/cancel/',
                metadata={
                    'user_id': str(request.user.id),
                    'token_count': str(token_count),
                    'company_id': str(company.company_id)
                }
            )
            return redirect(session.url, code=303)
        except Exception as e:
            return HttpResponseBadRequest(str(e))



def success_view(request):
    return render(request, "company/success.html")

def cancel_view(request):
    return render(request, "company/cancel.html")

# refunds


@login_required
def refund_client_token(request, token_id):
    if request.method == 'POST':
        try:
            token = Token.objects.get(id=token_id, used=False, refunded=False)
            token_company = token.company

            if token_company.manager != request.user:
                messages.error(request, 'You do not have permission to refund this token.')
                return redirect('view_client_tokens', client_id=token.user.id)

            # Ensure the token is linked to a purchase and that the purchase has a Stripe payment_intent
            if not token.purchase or not token.purchase.stripe_payment_intent_id:
                messages.error(request, 'Token does not have a valid payment intent for refund.')
                return redirect('view_client_tokens', client_id=token.user.id)

            # Get the TokenPurchase instance
            purchase = token.purchase
            if not purchase:
                messages.error(request, "No associated purchase found for this token.")
                return redirect('view_clients')

            payment_intent_id = purchase.stripe_payment_intent_id
            if not payment_intent_id:
                messages.error(request, "No Stripe PaymentIntent ID found for this token.")
                return redirect('view_clients')

            # Calculate cost per token in Stripe's smallest unit (e.g. 500 for £5.00)
            cost_per_token = int(purchase.get_cost_per_token() * 100)

            # Refund only one token’s cost
            refund = stripe.Refund.create(
                payment_intent=payment_intent_id,
                amount=cost_per_token,
                metadata={
                    "refunded_user": token.user.username,
                    "refunded_user_id": token.user.id,
                    "refunded_by": request.user.username,
                    "token_id": token.id
                }
            )
            # Mark token as refunded
            token.used = True
            token.refunded = True
            token.save()

            # Update refund request status if it exists
            refund_request = RefundRequest.objects.filter(token=token, user=token.user, status='Pending').first()
            if refund_request:
                refund_request.status = 'Approved'
                refund_request.reviewed_by = request.user
                refund_request.save()
                messages.success(request, 'Stripe refund issued and request marked approved.')
            else:
                RefundRequest.objects.create(
                    user=token.user,
                    token=token,
                    status='Approved',
                    reviewed_by=request.user
                )
                messages.success(request, 'Token refunded via Stripe successfully.')

        except Token.DoesNotExist:
            messages.error(request, 'Token not found or is not eligible for refund.')
        except stripe.error.StripeError as e:
            messages.error(request, f'Stripe error: {str(e)}')

    return redirect('view_clients')

import logging
from django.conf import settings
from django.http import HttpResponseBadRequest, HttpResponse
from django.views.decorators.csrf import csrf_exempt
import stripe
from django.contrib.auth import get_user_model
from company.models import Company, TokenPurchase, Token, UserProfile

User = get_user_model()
logger = logging.getLogger(__name__)

@csrf_exempt
def stripe_webhook(request):
    # This outer try-except will catch *any* unhandled exception
    # that occurs within the webhook function and log it.
    try:
        logger.info(f"Webhook received! Method: {request.method}, Path: {request.path}")

        payload = request.body
        sig_header = request.META.get('HTTP_STRIPE_SIGNATURE')
        endpoint_secret = settings.STRIPE_WEBHOOK_SECRET

        # Log the raw payload for debugging (be careful with sensitive data in production logs)
        # logger.info(f"Raw Payload: {payload.decode('utf-8')}")
        logger.info(f"Signature Header: {sig_header}")
        logger.info(f"Endpoint Secret (first 5 chars): {endpoint_secret[:5]}...") # Log part of secret for verification

        if not sig_header:
            logger.error("Missing Stripe signature header.")
            return HttpResponseBadRequest("Missing Stripe signature header.")

        try:
            event = stripe.Webhook.construct_event(payload, sig_header, endpoint_secret)
            logger.info(f"Stripe event constructed successfully. Type: {event['type']}")
        except (ValueError, stripe.error.SignatureVerificationError) as e:
            logger.error(f"Stripe webhook signature verification error: {e}", exc_info=True) # Ensure traceback is printed
            return HttpResponseBadRequest(f"Webhook signature verification failed: {e}")

        if event['type'] == 'checkout.session.completed':
            session = event['data']['object']
            logger.info(f"Checkout session completed event. Session ID: {session['id']}, Payment Status: {session.get('payment_status')}")

            if session.get("payment_status") != "paid":
                logger.warning(f"Payment status is not 'paid' for session {session['id']}. Status: {session.get('payment_status')}. Returning 200.")
                return HttpResponse(status=200)

            metadata = session.get('metadata', {})
            user_id = metadata.get('user_id')
            token_count_str = metadata.get('token_count')
            company_id = metadata.get('company_id')

            logger.info(f"Extracted Metadata: user_id={user_id}, token_count_str={token_count_str}, company_id={company_id}")

            if not all([user_id, token_count_str, company_id]):
                logger.error(f"Missing required metadata: user_id={user_id}, token_count={token_count_str}, company_id={company_id}")
                return HttpResponseBadRequest("Missing required metadata.")

            try:
                token_count = int(token_count_str)
            except (ValueError, TypeError):
                logger.error(f"Invalid token_count format: {token_count_str}", exc_info=True)
                return HttpResponseBadRequest("Invalid token count format.")

            try:
                user = User.objects.get(id=user_id)
                company = Company.objects.get(company_id=company_id)
                logger.info(f"User and Company found: {user.username}, {company.name}")

                total_price = token_count * company.token_price
                purchase = TokenPurchase.objects.create(
                    user=user,
                    company=company,
                    tokens_bought=token_count,
                    total_price=total_price,
                    stripe_payment_intent_id=session.get('payment_intent')
                )
                logger.info(f"TokenPurchase created: {purchase.id}")

                tokens_to_create = [
                    Token(user=user, company=company, purchase=purchase)
                    for _ in range(token_count)
                ]
                Token.objects.bulk_create(tokens_to_create)
                logger.info(f"{token_count} Tokens created.")

                # Send confirmation email to the user
                send_custom_email(
                    subject="Token Purchase Confirmation",
                    message=f"Dear {user.username},\n\nYou have successfully purchased {token_count} tokens for {company.name}. Total price: £{total_price}. Thank you for your purchase!\n\nBest regards,\nClassifyBooking Team",
                    recipient_list=[user.email]
                )
                logger.info(f"Confirmation email sent to {user.email}.")

                profile = getattr(user, 'profile', None)
                if profile:
                    profile.token_count += token_count
                    profile.save()
                    logger.info(f"UserProfile token_count updated for {user.username}. New count: {profile.token_count}")
                else:
                    logger.error(f"UserProfile not found for user {user.username}. Cannot update token_count.")
                    return HttpResponseBadRequest("User profile missing for token update.")

            except Exception as e:
                logger.error(f"Error processing Stripe webhook: {e}", exc_info=True)
                return HttpResponseBadRequest(f"Error processing webhook: {e}")

        return HttpResponse(status=200)

    except Exception as e:
        # This catch-all will ensure any unexpected error is logged
        logger.critical(f"UNHANDLED EXCEPTION IN STRIPE WEBHOOK: {e}", exc_info=True)
        return HttpResponseBadRequest(f"An unexpected error occurred: {e}")


@login_required
def approve_refund_request(request, request_id):
    try:
        refund_request = RefundRequest.objects.get(
            id=request_id,
            token__company=request.user.profile.company,
            status='Pending'
        )
        token = refund_request.token
        purchase = token.purchase

        if not purchase:
            messages.error(request, 'Token is not eligible for refund.')
            return redirect('view_refund_requests')

        cost_per_token = purchase.get_cost_per_token()
        amount_to_refund = int(cost_per_token * 100)  # Stripe uses cents

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

        # Update token and refund request
        token.refunded = True
        token.used = True
        token.save()

        refund_request.status = 'Approved'
        refund_request.reviewed_by = request.user
        refund_request.save()

        send_custom_email(
        subject="Your Refund Request Has Been Approved",
        message="Your refund request has been approved. We'll notify you when it has been processed.",
        recipient_list=[refund_request.user.email]
    )


        messages.success(request, f'Token refunded and request approved. Stripe Refund ID: {refund.id}')
    except RefundRequest.DoesNotExist:
        messages.error(request, 'Refund request not found or does not belong to your company.')
    except stripe.error.StripeError as e:
        messages.error(request, f'Stripe error: {str(e)}')
    except Exception as e:
        messages.error(request, f'Unexpected error: {str(e)}')

    return redirect('view_refund_requests')