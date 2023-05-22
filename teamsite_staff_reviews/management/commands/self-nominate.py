from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.utils.timezone import now
from resourcing.models import Profile
from reviews.models import (
    Nomination,
    ReviewerRole,
    ReviewForm,
    ReviewFormQuestion,
    ReviewFormResponse,
    ReviewPeriod,
    ReviewRound,
    ReviewStage,
)

User = get_user_model()


class Command(BaseCommand):
    help = """
    Nominates Line Managers for the current review cycle
    """

    def add_arguments(self, parser):
        parser.add_argument("--exclude-file", "-x", nargs="?", type=str)

    def handle(self, *args, exclude_file, **options):
        excludes = []
        if exclude_file is not None:
            with open(exclude_file, "rt") as FILE:
                lines = FILE.readlines()
            excludes = [int(l) for l in lines]

        stage = (
            ReviewStage.objects.filter(
                code="OPEN",
                date__lte=now(),
            )
            .order_by("-date")
            .first()
        )
        if stage is None:
            print("No current review cycle found")
            return

        user_map = {}
        for user in Profile.objects.current():
            user_map[user.user.pk] = user.user

        for ex in excludes:
            try:
                user = user_map.pop(ex)
                if user is not None:
                    print(f"Excluding {user}")
            except KeyError:
                pass

        for user in user_map.values():
            nom, created = Nomination.objects.update_or_create(
                reviewee=user,
                reviewer=user,
                role=ReviewerRole.SELF_ASSESSMENT,
                period=stage.period,
            )
