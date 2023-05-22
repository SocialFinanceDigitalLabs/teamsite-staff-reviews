import yaml
from django.core.management import BaseCommand

from teamsite_staff_reviews.models import ReviewPeriod


class Command(BaseCommand):
    help = """
        Allows creation of custom forms and questions for a specific review period. 
        
        The period and year have to be specified in the configuration file.
        
        This functionality can also be performed through admin with the default forms.
    """

    def add_arguments(self, parser):
        parser.add_argument("filename", type=str)

    def handle(self, *args, filename, **options):
        print(f"Opening {filename}")
        with open(filename) as FILE:
            data = yaml.safe_load(FILE)

        print(f"Found data for {data['period']} {data['year']}")

        period = ReviewPeriod.objects.get(year=data["year"], round=data["period"])

        period.add_forms()
