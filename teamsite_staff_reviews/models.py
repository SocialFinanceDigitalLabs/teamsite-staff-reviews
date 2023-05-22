import secrets
import string
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict

from dateutil.relativedelta import MO, relativedelta
from django.contrib.auth import get_user_model
from django.db import models
from django.utils import timezone
from django.utils.timezone import now

User = get_user_model()

NOMINATIONS_OPEN_DESCRIPTION = """
Nominations are now open for reviewers. 

All Direct Reports should review their line managers. In addition, please select up to **three** project managers or directors for "manager" reviewers, and up to **three** peers or wider team members who you have worked closely with. 

External should only be used for those in predominantly external roles, such as IPS Grow. 

Please discuss your choices with your line manager. They will be able to see this list on their dashboard page.
""".strip()

NOMINATIONS_OPEN_CONFIG = {
    "LMInfo": "If you are a line manager, then you will be able to see who your line reports have nominated here. \n\n"
    "Please discuss the choices with them."
}

FEEDBACK_OPENS_DESCRIPTION = """
Please complete the review forms for each of the staff members below. 

Each form has a save button, and there is no separate submit button you have to click. The forms will auto-save every 30 seconds, but to make sure you don't lose any work, please click save before navigating away from the page or leaving your computer unattended. 

You should see a green message pop up to confirm that your work has been saved.
""".strip()

FEEDBACK_CLOSES_DESCRIPTION = """
Please find the submitted feedback on your line reports below. 

At the top of each section you will find the assessment form for you to complete by the 23 June.
""".strip()


class ReviewRound(models.TextChoices):
    FULL_YEAR = "FY", "Full Year"
    MID_YEAR = "MY", "Mid Year"


class ReviewerRole(models.TextChoices):
    PROJECT_MANAGER = "PM", "Project Manager"
    DIRECT_REPORT = "DR", "Direct Report"
    WIDER_TEAM = "WT", "Wider Team"
    EXTERNAL = "EX", "External"
    SELF_ASSESSMENT = "SA", "Self-Assessment"
    ASSESSMENT_PT_1 = "A1", "Assessment - Part 1"


class StageCode(Enum):
    OPEN = "Opens", dict(visible=False, morning=True)
    NOMINATIONS = "Nominations Open", dict(
        morning=True,
        description=NOMINATIONS_OPEN_DESCRIPTION,
        configuration=NOMINATIONS_OPEN_CONFIG,
    )
    NOMINATIONS_CLOSE = "Nominations Close"
    FEEDBACK_OPENS = "Feedback Opens", dict(
        morning=True, description=FEEDBACK_OPENS_DESCRIPTION
    )
    FEEDBACK_CLOSE = "Feedback Closes", dict(description=FEEDBACK_CLOSES_DESCRIPTION)
    PART1 = "Part 1", dict(title="Part 1 Appraisal Form to be submitted to HR")
    REVIEW_MEETINGS = "Review Meetings", dict(morning=True)
    ONE_ON_ONE = "1-on-1", dict(
        title="1:1 Meetings between Line Managers and Reports", morning=True
    )
    PART2 = "Part 2", dict(title="Part 2 Appraisal Form to be submitted to HR")
    OTHER = "Other"

    def __init__(self, label: str, config: dict = None):
        self._label = label
        self._config = config or {}

    @property
    def index(self):
        return list(type(self)).index(self)

    @property
    def morning(self):
        return self._config.get("morning", False)

    def get_time(self, reference_date: datetime):
        if self.morning:
            return reference_date.replace(hour=0, minute=0, second=0, microsecond=0)
        else:
            return reference_date.replace(hour=23, minute=59, second=59, microsecond=0)

    @property
    def visible(self):
        return self._config.get("visible", True)

    @property
    def label(self):
        return f"{self.index+1 }. {self._label}"

    @property
    def title(self):
        return self._config.get("title", self._label)

    @property
    def description(self):
        return self._config.get("description")

    @property
    def configuration(self):
        return self._config.get("configuration")

    @classmethod
    def choices(cls):
        return tuple((i.name, i.label) for i in cls)


class ReviewPeriodQuerySet(models.QuerySet):
    def get_current(self):
        return (
            self.filter(
                stages__code="OPEN",
                stages__date__lte=now(),
            )
            .order_by("-stages__date")
            .first()
        )

    def round(self, value):
        year, period = value.split(" ", 1)
        year = int(year)
        period = ReviewRound(period)
        return self.filter(year=year, period=period).first()


class ReviewPeriod(models.Model):
    year = models.IntegerField()
    round = models.CharField(max_length=2, choices=ReviewRound.choices)

    objects = ReviewPeriodQuerySet.as_manager()

    class Meta:
        unique_together = ["year", "round"]

    @property
    def round_label(self):
        return ReviewRound(self.round).label

    def add_default_stages(self):
        current_date = timezone.now().replace(
            hour=12, minute=0, second=0, microsecond=0
        )
        current_date += relativedelta(weekday=MO(1))

        for stage in StageCode:
            if stage != StageCode.OTHER:
                stage, created = ReviewStage.objects.get_or_create(
                    period=self,
                    code=stage.name,
                    defaults={
                        "date": stage.get_time(current_date),
                        "visible": stage.visible,
                        "title": stage.title,
                        "description": stage.description,
                        "configuration": stage.configuration,
                    },
                )

                current_date = stage.date + timedelta(weeks=1)

    def add_forms(self, **kwargs):
        from teamsite_staff_reviews.workflow import create_review_form

        create_review_form(self, **kwargs)

    def nominate_line_managers(self):
        from teamsite_staff_reviews.workflow import nominate_line_managers as nominate

        nominate(self)

    def __str__(self):
        return f"{self.year} {self.round_label}"


class ReviewStageQuerySet(models.QuerySet):
    def get_current(self):
        return (
            self.filter(
                date__lte=now(),
            )
            .order_by("-date")
            .first()
        )


class ReviewStage(models.Model):
    period = models.ForeignKey(
        ReviewPeriod, on_delete=models.CASCADE, related_name="stages"
    )
    code = models.CharField(max_length=50, choices=StageCode.choices())
    title = models.CharField(max_length=255)
    visible = models.BooleanField(default=True)
    description = models.TextField(null=True, blank=True)
    configuration = models.TextField(null=True, blank=True)
    date = models.DateTimeField()

    objects = ReviewStageQuerySet.as_manager()

    class Meta:
        ordering = ["date"]


class Nomination(models.Model):
    reviewee = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="reviewee_nominations"
    )
    reviewer = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="reviewer_nominations",
        null=True,
        blank=True,
    )
    external_name = models.CharField(max_length=100, null=True, blank=True)
    external_email = models.EmailField(null=True, blank=True)
    role = models.CharField(max_length=2, choices=ReviewerRole.choices)
    period = models.ForeignKey(
        ReviewPeriod, on_delete=models.CASCADE, related_name="nominations"
    )

    closes_override = models.DateTimeField(null=True, blank=True)

    @property
    def form(self):
        return ReviewForm.objects.get(period=self.period, role=self.role)

    @property
    def reviewer_name(self):
        if self.external_name:
            return self.external_name
        else:
            return f"{self.reviewer.first_name} {self.reviewer.last_name}"

    @property
    def closes(self):
        if self.closes_override is not None:
            return self.closes_override
        else:
            try:
                return ReviewStage.objects.get(
                    period=self.period, code="FEEDBACK_CLOSE"
                ).date
            except ReviewStage.DoesNotExist:
                return None

    def __str__(self):
        if self.external_name or self.external_email:
            return f"{self.external_name} ({self.external_email}) => {self.reviewee.profile.short_name}"
        else:
            return f"{self.reviewer.profile.short_name} ({self.role}) => {self.reviewee.profile.short_name}"

    class Meta:
        unique_together = ["reviewee", "reviewer", "external_email"]
        ordering = ["reviewer__username", "reviewee__username"]


class ReviewForm(models.Model):
    period = models.ForeignKey(
        ReviewPeriod, on_delete=models.CASCADE, related_name="forms"
    )
    role = models.CharField(max_length=2, choices=ReviewerRole.choices)
    title = models.CharField(max_length=255)
    description = models.TextField(null=True, blank=True)

    class Meta:
        unique_together = ["role", "period"]

    @property
    def role_label(self):
        return ReviewerRole(self.role).label

    def __str__(self):
        return f"{self.period} {self.title}"


class ReviewFormQuestion(models.Model):
    form = models.ForeignKey(
        ReviewForm, on_delete=models.CASCADE, related_name="questions"
    )
    sequence = models.IntegerField()
    title = models.CharField(max_length=255)
    description = models.TextField(null=True, blank=True)

    class Meta:
        ordering = ["form", "sequence"]

    def __str__(self):
        return f"{self.form} - {self.sequence} - {self.title}"


class ReviewFormResponse(models.Model):
    nomination = models.ForeignKey(
        Nomination, on_delete=models.CASCADE, related_name="responses"
    )
    question = models.ForeignKey(
        ReviewFormQuestion, on_delete=models.CASCADE, related_name="responses"
    )
    value = models.TextField(null=True, blank=True)

    created = models.DateTimeField(blank=True, auto_now_add=True)
    last_modified = models.DateTimeField(blank=True, auto_now=True)

    class Meta:
        unique_together = ["nomination", "question"]


class ExternalUser(models.Model):
    email = models.EmailField(unique=True)
    name = models.CharField(max_length=255, null=True, blank=True)
    failure_count = models.SmallIntegerField(default=0)
    is_enabled = models.BooleanField(default=True)

    def __str__(self):
        return f"({self.pk}) {self.email}{'' if self.is_enabled else ' disabled'}"


class ExternalInvitation(models.Model):
    nomination = models.OneToOneField(
        Nomination,
        on_delete=models.CASCADE,
        related_name="invitation",
        primary_key=True,
    )
    user = models.ForeignKey(
        ExternalUser,
        on_delete=models.CASCADE,
        related_name="invitations",
        null=True,
        blank=True,
    )
    code = models.PositiveIntegerField(unique=True, blank=True)

    def save(self, *args, **kwargs):
        if not self.code:
            self.generate_code()
        super(ExternalInvitation, self).save(*args, **kwargs)

    def generate_code(self):
        value = 0
        while value < 100000:
            value = int("".join(secrets.choice(string.digits) for i in range(6)))
        self.code = value

    def __str__(self):
        return f"{self.nomination}"


class ExternalInvitationMessage(models.Model):
    invitation = models.ForeignKey(
        ExternalInvitation, on_delete=models.CASCADE, related_name="messages"
    )
    sent_time = models.DateTimeField(auto_now_add=True)
    sent_to = models.EmailField()
    sent_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name="+")
    message = models.TextField(null=True, blank=True)


class ExternalUserToken(models.Model):
    email = models.EmailField()
    code = models.PositiveIntegerField(null=True)

    secret = models.CharField(max_length=100)
    expiry = models.DateTimeField()
    redeemed = models.DateTimeField(null=True, blank=True)
    client_ip = models.GenericIPAddressField(null=True, blank=True)

    def save(self, *args, **kwargs):
        if not self.secret:
            self.secret = secrets.token_urlsafe(50)
        if not self.expiry:
            self.expiry = now() + timedelta(minutes=120)
        super(ExternalUserToken, self).save(*args, **kwargs)

    @property
    def expired(self):
        return self.expiry < now()


class ExternalNominationManager(models.Manager):
    def all(self):
        return super().filter(role=ReviewerRole.EXTERNAL)


class ExternalNomination(Nomination):
    """
    A pseudo-model to make it easier to manage external nominations
    """

    objects = ExternalNominationManager()

    class Meta:
        proxy = True
