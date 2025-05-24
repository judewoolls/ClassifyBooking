from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from .forms import CreateCompanyForm, ChangeCompanyDetailsForm
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
from .models import Coach

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
            return redirect('company_dashboard')  # update this to your URL name
    else:
        form = ChangeCompanyDetailsForm(instance=request.user.profile.company)

    return render(request, 'company/change_company_details.html', {'form': form})