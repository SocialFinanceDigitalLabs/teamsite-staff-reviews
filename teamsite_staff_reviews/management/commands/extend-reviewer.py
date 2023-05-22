from datetime import datetime

from django.contrib.auth import get_user_model
from django.core.management import BaseCommand
from django.utils.timezone import make_aware
from reviews.models import Nomination, ReviewPeriod

User = get_user_model()


class Command(BaseCommand):
    help = """
    Sets deadline for a reviewer
    """

    def add_arguments(self, parser):
        parser.add_argument("reviewer", type=str)
        parser.add_argument("date", type=str, nargs="?")

    def handle(self, *args, reviewer, date, **options):
        period = ReviewPeriod.objects.get_current()
        if period is None:
            print("No current review cycle found")
            return

        if date is not None:
            date = make_aware(datetime.fromisoformat(date))

        user = User.objects.get(username__icontains=reviewer)
        noms = Nomination.objects.filter(reviewer=user, period=period)
        for n in noms:
            print("Updating closes for", n, date)
            n.closes_override = date
            n.save()
