from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.utils.timezone import now
from reviews.models import Nomination, ReviewerRole, ReviewStage

User = get_user_model()


class Command(BaseCommand):
    help = """
    Nominates Line Managers for the current review cycle
    """

    def add_arguments(self, parser):
        parser.add_argument("--report", action="store_true", default=False)
        parser.add_argument("--create", action="store_true", default=False)

    def handle(self, *args, report, create, **options):
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

        period = stage.period

        closes_stage = ReviewStage.objects.filter(code="PART1", period=period).first()

        if report:
            self.report(closes_stage)

        if create:
            self.create(closes_stage)

    def report(self, closes_stage):
        reviewee_list = Nomination.objects.filter(
            period=closes_stage.period
        ).values_list("reviewee", flat=True)
        for reviewee in set(reviewee_list):
            reviewee = User.objects.get(pk=reviewee)
            line_manager = reviewee.profile.line_manager
            if line_manager is None:
                print("No line manager found for", reviewee)
            else:
                try:
                    nom = Nomination.objects.get(
                        period=closes_stage.period,
                        role=ReviewerRole.ASSESSMENT_PT_1,
                        reviewer=line_manager,
                        reviewee=reviewee,
                    )
                except Nomination.DoesNotExist:
                    print(
                        f"No nomination found for {line_manager} to assess {reviewee}"
                    )

    def create(self, closes_stage):
        direct_reports = Nomination.objects.filter(
            period=closes_stage.period, role=ReviewerRole.DIRECT_REPORT
        )
        for dr in direct_reports:
            if dr.reviewer is not None:
                nom, created = Nomination.objects.get_or_create(
                    period=closes_stage.period,
                    role=ReviewerRole.ASSESSMENT_PT_1,
                    reviewer=dr.reviewee,
                    reviewee=dr.reviewer,
                    defaults=dict(
                        closes_override=closes_stage.date,
                    ),
                )
                if not created:
                    nom.closes_override = closes_stage.date
                    nom.save()
                print(
                    f"{'Created' if created else 'Updated'} nomination for {nom.reviewer} to assess {nom.reviewee}"
                )
