from django.core.management import BaseCommand
from reviews.models import ReviewPeriod
from reviews.reports.review_export.exporter import (
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
        parser.add_argument("--task-name", type=str, nargs="?")
        parser.add_argument("location", type=str, default="sharepoint:feedback:")

    def handle(self, *args, location, task_name, **options):
        period = ReviewPeriod.objects.get_current()
        if period is None:
            print("No current review cycle found")
            return

        if location.startswith("sharepoint:"):
            saver = save_to_sharepoint(location)
        else:
            saver = save_to_fs(location)

        export_by_reviewee(
            saver, period=period, task_name=task_name, export_reviewee=True
        )
