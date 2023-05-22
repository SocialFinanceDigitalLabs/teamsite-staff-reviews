from django.contrib.auth import get_user_model
from django.core.management import BaseCommand
from office365.api.auth import get_token
from office365.api.sharepoint.file import get_file_metadata, grant_permission
from office365.api.sharepoint.util import parse_sharepoint_path
from reviews.models import Nomination, ReviewPeriod

User = get_user_model()


class Command(BaseCommand):
    help = """
    Invites line managers
    """

    def handle(self, *args, **options):
        period = ReviewPeriod.objects.get_current()
        if period is None:
            print("No current review cycle found")
            return

        location = "feedback:"

        reviewee_ids = set()
        for r in Nomination.objects.filter(period=period).values("reviewee").distinct():
            reviewee_ids.add(r["reviewee"])

        users = User.objects.filter(id__in=reviewee_ids)
        for user in users:
            line_manager = user.profile.line_manager
            if line_manager is None:
                print(f"No line manager for {user.first_name} {user.last_name}")
                continue
            first_name = user.first_name
            last_name = user.last_name
            email = line_manager.email

            dir = f"{period}/responses/{first_name} {last_name}"
            print(dir, "to", email)

            try:
                access_token = get_token()
                drive, filename = parse_sharepoint_path(
                    f"{location}/{dir}", access_token=access_token
                )
                metadata = get_file_metadata(
                    drive["id"], filename, access_token=access_token
                )
                grant_permission(drive["id"], metadata["id"], email)
            except:
                print(f"Skipping {dir}")
                pass
