from pathlib import Path
from tempfile import TemporaryDirectory

import requests
from django.core.management import BaseCommand
from django.db.models import Q
from office365.api.auth import get_token
from office365.api.sharepoint import API_URL
from reviews.models import Nomination, ReviewerRole, ReviewPeriod, User
from reviews.util.word_export.assessment_pt2 import AssessmentDocumentPart2
from reviews.util.word_export.review import ReviewDocument


class Command(BaseCommand):
    help = """
    Exports review documents
    """

    def add_arguments(self, parser):
        parser.add_argument("--users", "-u", type=str, nargs="*")
        parser.add_argument("--users-resume-from", "-ur", type=str, nargs="?")
        parser.add_argument("--line-manager", "-lm", action="store_true")
        parser.add_argument("--feedback-given", "-fg", action="store_true")
        parser.add_argument("--print-folder", "-pf", action="store_true")

    def handle(
        self,
        *args,
        users,
        line_manager,
        feedback_given,
        users_resume_from,
        print_folder,
        **options,
    ):
        period = ReviewPeriod.objects.get_current()
        if period is None:
            print("No current review cycle found")
            return

        if users:
            users = [User.objects.get(username__icontains=name) for name in users]
        elif users_resume_from:
            users = User.objects.filter(username__gte=users_resume_from)

        if print_folder:
            print_folder_link(period, users)

        if line_manager:
            upload_line_manager_files(period, users)

        if feedback_given:
            upload_feedback_provided(period, users)


def print_folder_link(period, users):
    access_token = get_token()
    for user in users:
        params = {
            "Authorization": f"Bearer {access_token}",
        }
        response = requests.get(
            f"{API_URL}/users/{user.email}/drive/special/documents:/HR Matters",
            headers=params,
        )
        response.raise_for_status()
        data = response.json()
        print(user.profile.short_name, data.get("webUrl"))


def upload_file(
    user, filename, bytes, content_type="application/binary", access_token=None
):
    if len(bytes) / 1024**2 > 4:
        raise Exception("Large file upload not currently implemented")

    if access_token is None:
        access_token = get_token()

    params = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": content_type,
    }
    response = requests.put(
        f"{API_URL}/users/{user.email}/drive/special/documents:/HR Matters/{filename}:/content",
        headers=params,
        data=bytes,
    )
    response.raise_for_status()
    return response.json()


def save_file_to_sharepoint(path, owner_user, filename):
    access_token = get_token()
    print(owner_user.email, filename)
    try:
        with open(path, "rb") as FILE:
            data = FILE.read()
            upload_file(owner_user, filename, data, access_token=access_token)
    except Exception as e:
        print(" ** FAILED TO UPLOAD", e)


def upload_line_manager_files(period, users=None):
    # First we create PT2 forms
    nom_query = Nomination.objects.filter(
        period=period, role=ReviewerRole.ASSESSMENT_PT_1
    )
    if users:
        nom_query = nom_query.filter(reviewer__in=users)

    period_name = f"{period}"

    for nom in nom_query:
        report = nom.reviewee
        name = f"{report.first_name} {report.last_name}"
        with TemporaryDirectory() as dirname:
            path = Path(dirname) / "review.docx"
            doc = AssessmentDocumentPart2(nom)
            doc.save(path.absolute())

            save_file_to_sharepoint(
                path, nom.reviewer, f"{period_name}/Reports/{name}/Appraisal Form.docx"
            )

        for report_nom in Nomination.objects.filter(
            ~Q(role=ReviewerRole.ASSESSMENT_PT_1),
            period=period,
            reviewee=report,
        ):
            with TemporaryDirectory() as dirname:
                path = Path(dirname) / "review.docx"
                doc = ReviewDocument(report_nom)
                doc.save(path.absolute())

                if report_nom.external_name:
                    reviewer = report_nom.external_name
                else:
                    reviewer = f"{report_nom.reviewer.first_name} {report_nom.reviewer.last_name}"

                filename = f"{ReviewerRole(report_nom.role).label}"
                if report_nom.role != ReviewerRole.SELF_ASSESSMENT:
                    filename += f" - {reviewer}"

                filename = f"{period_name}/Reports/{name}/{filename}.docx"

                save_file_to_sharepoint(path, nom.reviewer, filename)


def upload_feedback_provided(period, users=None):
    # Then we export all provided
    nom_query = Nomination.objects.filter(period=period).exclude(
        role=ReviewerRole.ASSESSMENT_PT_1
    )
    if users:
        nom_query = nom_query.filter(reviewer__in=users)

    period_name = f"{period}"

    for nom in nom_query:
        reviewee = nom.reviewee
        name = f"{reviewee.first_name} {reviewee.last_name}"
        with TemporaryDirectory() as dirname:
            path = Path(dirname) / "review.docx"
            doc = ReviewDocument(nom)
            doc.save(path.absolute())

            save_file_to_sharepoint(
                path,
                nom.reviewer,
                f"{period_name}/Feedback Provided/{ReviewerRole(nom.role).label} - {name}.docx",
            )
