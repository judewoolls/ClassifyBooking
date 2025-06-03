from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from .forms import CreateCompanyForm, ChangeCompanyDetailsForm, AddCoachForm, RemoveCoachForm, RemoveClientForm
from django.contrib import messages
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
from .models import Coach
from django.contrib.auth import get_user_model

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
            return render(request, 'company/company_user_dashboard.html', {'company': company})
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

def remove_coach(request):
    if request.method == 'POST':
        form = RemoveCoachForm(request.POST, user=request.user)
        if form.is_valid():
            coach = form.cleaned_data.get('coach')
            if coach:
                coach.delete()
                messages.success(request, 'Coach removed successfully.')
                return redirect('company_dashboard')  # Correct redirect
            else:
                messages.error(request, 'Coach not found or does not belong to your company.')
                return redirect('company_dashboard')  # Correct redirect
    else:
        form = RemoveCoachForm(user=request.user)
    return render(request, 'company/remove_coach.html', {'form': form,
                                                          'company': request.user.profile.company})


def remove_client(request):
    if request.method == 'POST':
        form = RemoveClientForm(request.POST, user=request.user)
        if form.is_valid():
            client = form.cleaned_data.get('client')
            if client:
                if Coach.objects.filter(coach=client).exists():
                    messages.error(request, 'Client is also a coach and cannot be removed as a client.')
                    return redirect('company_dashboard')
                client.profile.company = None
                client.profile.save()
                messages.success(request, 'Client removed successfully.')
                return redirect('company_dashboard')
            else:
                messages.error(request, 'Client not found or does not belong to your company.')
                return redirect('company_dashboard')
        else:
            messages.error(request, 'Form is not valid.')
            return redirect('company_dashboard')
    else:
        return render(request, 'company/remove_client.html', {'company': request.user.profile.company,
                                                              'form': RemoveClientForm(user=request.user)})