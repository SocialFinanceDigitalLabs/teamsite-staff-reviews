from datetime import datetime

from django.contrib.auth import get_user_model
from django.core.management import BaseCommand
from django.utils.timezone import make_aware
from reviews.models import Nomination, ReviewerRole, ReviewPeriod

User = get_user_model()


class Command(BaseCommand):
    help = """
    Sets deadline for a particular reviewer role (and optionally user)
    """

    def add_arguments(self, parser):
        parser.add_argument("role", type=str, default="A1")
        parser.add_argument("date", type=str)
        parser.add_argument("--user", "-u", type=str, nargs="?")

    def handle(self, *args, role, date, user, **options):
        period = ReviewPeriod.objects.get_current()
        if period is None:
            print("No current review cycle found")
            return

        if date is not None:
            date = make_aware(datetime.fromisoformat(date))

        role = ReviewerRole(role)
        noms = Nomination.objects.filter(role=role, period=period)
        if user is not None:
            user = User.objects.get(email__icontains=user)
            noms = noms.filter(reviewer=user)

        for n in noms:
            print("Updating closes for", n, date)
            n.closes_override = date
            n.save()
