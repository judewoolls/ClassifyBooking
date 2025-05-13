from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required

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
        return render(request, 'company/create_company.html')