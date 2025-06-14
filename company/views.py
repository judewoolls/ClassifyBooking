from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from .forms import CreateCompanyForm, ChangeCompanyDetailsForm, AddCoachForm, RemoveCoachForm, AddVenueForm, EditVenueForm, PurchaseTokenForm
from booking.models import Booking
from django.contrib import messages
from django.contrib.auth.models import User
from .models import Coach, Token, Venue, RefundRequest
from django.contrib.auth import get_user_model
from django.shortcuts import get_object_or_404
from django.core.exceptions import ObjectDoesNotExist
from django.db.models import Case, When, IntegerField

@login_required
def company_dashboard(request):
    # Get the user's profile and associated company
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
            })
    
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
            if client.profile.company == request.user.profile.company:
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
    # except Exception as e:
    #     messages.error(request, f'An error occurred while fetching venues: {str(e)}')
    #     return redirect('company_dashboard')
    
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
        form = PurchaseTokenForm(request.POST, user=request.user)  # Pass the user to the form
        if form.is_valid():
            token_count = form.cleaned_data['token_count']
            company = request.user.profile.company
            if company:
                # Create tokens for the user
                for _ in range(token_count):
                    Token.objects.create(user=request.user, company=company)
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
            messages.success(request, 'Token marked for refund successfully and refund request has been sent')
        except Token.DoesNotExist:
            messages.error(request, 'Token not found or is not eligible for refund.')
    return redirect('company_dashboard')

@login_required
def refund_client_token(request, token_id):
    if request.method == 'POST':
        try:
            token = Token.objects.get(id=token_id, used=False, refunded=False)
            token_company = token.company
            if token_company.manager != request.user:
                messages.error(request, 'You do not have permission to refund this token.')
                return redirect('view_client_tokens', client_id=token.user.id)
            token.used = True
            token.refunded = True
            token.save()
            refund_request = RefundRequest.objects.filter(token=token, user=token.user, status='Pending').first()
            if refund_request:
                refund_request.status = 'Approved'
                refund_request.reviewed_by = request.user
                refund_request.save()
                messages.success(request, 'Token refund request approved successfully.')
            else:
                refund_request = RefundRequest.objects.create(
                    user=token.user,
                    token=token,
                    status='Approved',
                    reviewed_by=request.user
                )
                messages.success(request, 'Token marked as refunded successfully and refund is being sent.')
        except Token.DoesNotExist:
            messages.error(request, 'Token not found or is not eligible for refund.')
    return redirect('view_clients')

@login_required
def view_refund_requests(request):
    if not request.user.is_authenticated or not hasattr(request.user, 'profile') or not request.user.profile.company:
        messages.error(request, 'You do not have a company associated with your profile.')
        return redirect('company_dashboard')

    refund_requests = RefundRequest.objects.filter(token__company=request.user.profile.company).annotate(
        status_priority=Case(
            When(status='Pending', then=1),
            When(status='Approved', then=2),
            default=3,
            output_field=IntegerField()
        )
    ).order_by('status_priority', '-created_at')
    if not refund_requests:
        messages.info(request, 'No refund requests found for your company.')
    else:
        messages.success(request, f'Found {refund_requests.count()} refund requests for your company.')

    return render(request, 'company/view_refund_requests.html', {'refund_requests': refund_requests,
                                                                  'company': request.user.profile.company})

@login_required
def approve_refund_request(request, request_id):
    try:
        refund_request = RefundRequest.objects.get(id=request_id, token__company=request.user.profile.company)
        refund_request.status = 'Approved'
        refund_request.reviewed_by = request.user
        refund_request.save()
        messages.success(request, 'Refund request approved successfully.')
    except RefundRequest.DoesNotExist:
        messages.error(request, 'Refund request not found or does not belong to your company.')

    return redirect('view_refund_requests')

@login_required
def deny_refund_request(request, request_id):
    try:
        refund_request = RefundRequest.objects.get(id=request_id, token__company=request.user.profile.company)
        refund_request.status = 'Denied'
        refund_request.reviewed_by = request.user
        try:
            refund_request.token.used = False  # Mark the token as used
            refund_request.token.refunded = False  # Mark the token as refunded
            refund_request.token.save()
        except Token.DoesNotExist:
            messages.error(request, 'Token associated with this refund request does not exist.')
            return redirect('view_refund_requests')
        refund_request.save()
        messages.success(request, 'Refund request denied successfully. Token returned to client')
    except RefundRequest.DoesNotExist:
        messages.error(request, 'Refund request not found or does not belong to your company.')

    return redirect('view_refund_requests')