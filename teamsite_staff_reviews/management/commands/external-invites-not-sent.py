import tablib
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.utils.timezone import now
from resourcing.models import Profile
from reviews.models import (
    ExternalInvitation,
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
        Print externals reviews not sent
    """

    def handle(self, *args, **options):
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

        invitations = ExternalInvitation.objects.filter(nomination__period=stage.period)

        data = tablib.Dataset(headers=["First Name", "Email"])
        for inv in invitations:
            if inv.messages.count() == 0:
                data.append(
                    [
                        inv.nomination.reviewee.first_name,
                        inv.nomination.reviewee.email,
                    ]
                )

        print(data.export("csv"))
