from io import StringIO

from django.core.management import call_command
from django.test import TestCase

from teamsite_staff_reviews.models import ReviewPeriod, ReviewRound


class ParseBankHolidaysTest(TestCase):
    def call_command(self, *args, **kwargs):
        out = StringIO()
        call_command(
            "import-review-forms",
            *args,
            stdout=out,
            stderr=StringIO(),
            **kwargs,
        )
        return out.getvalue()

    def test_import(self):
        period = ReviewPeriod.objects.create(year=2022, round=ReviewRound.MID_YEAR)
        assert period.forms.count() == 0

        out = self.call_command("teamsite_staff_reviews/fixtures/2022MY.yml")

        assert period.forms.count() == 6
