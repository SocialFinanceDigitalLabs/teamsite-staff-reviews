import logging
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Dict, List, Tuple

from django.db.models import QuerySet
from office365.api.sharepoint.file import upload_file
from office365.api.sharepoint.util import parse_sharepoint_path
from reviews.models import Nomination, ReviewerRole
from reviews.util.word_export.assessment import AssessmentDocument
from reviews.util.word_export.review import ReviewDocument

logger = logging.getLogger(__name__)


def nomination_to_word(nomination: Nomination, filename):
    """
    Export a nomination to a Word document.
    :param nomination:
    :param filename:
    :return:
    """
    if nomination.role == ReviewerRole.ASSESSMENT_PT_1:
        document = AssessmentDocument(nomination)
        document.save(filename)
    else:
        document = ReviewDocument(nomination)
        document.save(filename)


def nomination_list_to_word(nomination_list: List[Nomination], filename):
    """
    Export a list of nominations to a Word document.
    :param nomination_list:
    :param filename:
    :return:
    """
    document = ReviewDocument(*nomination_list)
    document.save(filename)


def export_nominations(nomination_query: QuerySet) -> Tuple[Nomination, Path]:
    """
    A generator that yields a tuple of (nomination, path) for each nomination in the query.

    :param nomination_query: The nominations to export.
    :return:
    """
    with TemporaryDirectory() as dirname:
        reviewee_set = set()
        for nomination in nomination_query.order_by("reviewee__username"):
            reviewee_set.add((nomination.reviewee_id, nomination.period_id))
            path = Path(dirname) / f"nomination-{nomination.pk}.docx"
            nomination_to_word(nomination, path.absolute())
            yield nomination, path


def export_grouped_nominations(
    nomination_query: QuerySet, order_by: str
) -> Tuple[Dict, Path]:
    """
    A generator that yields a tuple of (nomination info, path) for a summary documentation for each nomination
    group in the query. Nominations are grouped by the 'order_by' argument.

    :param nomination_query: The nominations to export.
    :param order_by: The field to group by.
    :return:
    """
    with TemporaryDirectory() as dirname:

        def flush(group, nominations: List[Nomination]):
            if group is None:
                return None
            if len(nominations) == 0:
                yield None
            path = Path(dirname) / f"reviewee-{group}.docx"
            nomination_list_to_word(nominations, path.absolute())
            yield dict(order_by=order_by, group=group, nominations=nominations), path

        last_group = None
        group_members: List[Nomination] = []
        for nomination in nomination_query.order_by(order_by):
            group = getattr(nomination, order_by)
            if group != last_group:
                for r in flush(last_group, group_members):
                    if r is not None:
                        yield r
            last_group = group
            group_members.append(nomination)
        for r in flush(last_group, group_members):
            if r is not None:
                yield r


def save_to_fs(location):
    if location is None or location == "":
        location = "."

    def saver(path, dir, filename):
        dir = Path(location) / dir
        dir.mkdir(parents=True, exist_ok=True)
        filename = dir / filename
        Path(path).rename(filename)
        logger.info(f"Saved {filename}")

    return saver


def save_to_sharepoint(location):
    def saver(path, dir, filename):
        drive, filename = parse_sharepoint_path(f"{location}/{dir}/{filename}")
        with open(path, "rb") as FILE:
            data = FILE.read()
        upload_file(drive["id"], filename, data)
        logger.info(f"Uploaded {filename}")

    return saver
