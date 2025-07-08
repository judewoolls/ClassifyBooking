from django.core.management.base import BaseCommand
from django.utils.timezone import now
from datetime import timedelta
from company.models import Company 
from booking.utils import generate_schedule_for_date 

class Command(BaseCommand):
    help = "Generates schedule 30 days in advance for companies with auto-update enabled."

    def handle(self, *args, **kwargs):
        target_date = now().date() + timedelta(days=30)

        companies = Company.objects.filter(auto_updates=True)

        total_created = 0
        for company in companies:
            created = generate_schedule_for_date(company, target_date)
            total_created += created
            self.stdout.write(f"{company.name}: {created} events created")

        self.stdout.write(self.style.SUCCESS(f"Total events created: {total_created}"))
