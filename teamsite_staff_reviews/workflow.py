import logging
from pathlib import Path

import yaml

from . import fixtures
from .models import (
    Nomination,
    ReviewerRole,
    ReviewForm,
    ReviewFormQuestion,
    ReviewPeriod,
)

log = logging.getLogger(__name__)


def create_review_form(period: ReviewPeriod, configuration=None):
    if configuration is None:
        configuration = Path(fixtures.__file__).parent / "current-questions.yml"
    if not isinstance(configuration, dict):
        with open(configuration) as FILE:
            configuration = yaml.safe_load(FILE)

    for formdata in configuration["forms"]:
        form, created = ReviewForm.objects.update_or_create(
            period=period, role=formdata["role"]
        )
        form.title = formdata.get("title")
        form.description = formdata.get("description")
        form.save()

        for ix, questiondata in enumerate(formdata["questions"]):
            question, created = ReviewFormQuestion.objects.update_or_create(
                form=form,
                sequence=ix + 1,
                defaults={
                    "title": questiondata["title"],
                },
            )
            question.title = questiondata["title"]
            question.description = questiondata.get("description")
            question.save()


def nominate_line_managers(period: ReviewPeriod):
    from resourcing.models import Profile

    for user in Profile.objects.current():
        line_manager = user.line_manager
        if line_manager is None:
            log.error(f"NominateLineManager: No LM for {user}")
        elif not line_manager.profile.current:
            log.error(
                f"NominateLineManager: LM {line_manager} not a current staffer for {user}"
            )
        else:
            Nomination.objects.update_or_create(
                period=period,
                reviewer=user.user,
                role=ReviewerRole.DIRECT_REPORT,
                defaults=dict(reviewee=line_manager),
            )
