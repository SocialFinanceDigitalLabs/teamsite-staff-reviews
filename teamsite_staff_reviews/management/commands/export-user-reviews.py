from django.contrib.auth import get_user_model
from django.core.management import BaseCommand
from reviews.models import Nomination, ReviewPeriod
from reviews.reports.review_export.exporter import nomination_list_to_word

User = get_user_model()


class Command(BaseCommand):
    help = """
    Exports review documents
    """

    def add_arguments(self, parser):
        parser.add_argument("user", type=str)
        parser.add_argument("--filename", "-f", type=str, nargs="?", default=None)

    def handle(self, *args, user, filename, **options):
        period = ReviewPeriod.objects.get_current()
        if period is None:
            print("No current review cycle found")
            return

        reviewee = User.objects.get(username__icontains=user)
        nomination_list = Nomination.objects.filter(period=period, reviewee=reviewee)

        if filename is None:
            filename = f"{reviewee.first_name} {reviewee.last_name}.docx"

        nomination_list_to_word(nomination_list, filename)
        print(f"Wrote to {filename}")
