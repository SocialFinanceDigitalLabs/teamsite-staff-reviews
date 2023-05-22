from django.core.management import BaseCommand
from reviews.models import Nomination, ReviewerRole, ReviewPeriod, User
from reviews.reports.review_export.exporter import (
    __export_nominations,
    export_all_assessments,
    export_by_reviewee,
    export_nominations,
    save_to_fs,
    save_to_sharepoint,
)


class Command(BaseCommand):
    help = """
    Exports review documents
    """

    def add_arguments(self, parser):
        parser.add_argument("location", type=str, default="sharepoint:feedback:")
        parser.add_argument("--user", "-u", type=str, nargs="?")

    def handle(self, *args, location, user, **options):
        period = ReviewPeriod.objects.get_current()
        if period is None:
            print("No current review cycle found")
            return

        query = dict(period=period)

        if user is not None:
            query["reviewee"] = User.objects.get(email__icontains=user)

        if location.startswith("sharepoint:"):
            saver = save_to_sharepoint(location)
        else:
            saver = save_to_fs(location)

        export_all_assessments(saver, **query)
