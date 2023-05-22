# import logging
# from datetime import timedelta
# from pathlib import Path
# from tempfile import TemporaryDirectory

# from celery import shared_task
# from django.db.models import Q
# from msgraphy.domains.files import FilesGraphApi

# from office365.api import get_api
# from resourcing.reports.complete.complete_export import generate_report, get_models
# from reviews.models import Nomination, ReviewerRole, ReviewFormResponse, ReviewPeriod
# from reviews.reports.review_export.exporter import (
#     export_grouped_nominations,
#     export_nominations,
#     save_to_sharepoint,
# )
# from teamsite.models import ChangeLogEntry
# from teamsite.util.changetask import TaskArgs, changetask

# report_file = Path(__file__).parent / "../reports/report.yaml"
# sources_file = Path(__file__).parent / "../reports/sources.yaml"

# api: FilesGraphApi = get_api().files

# logger = logging.getLogger(__name__)


# @shared_task
# def export_data(
#     target_file,
#     task_name="EXPORT_REVIEW_DATA",
#     min_interval=timedelta(minutes=5),
#     refresh_interval=timedelta(days=1),
#     **kwargs,
# ):
#     models = get_models(report_file=report_file, sources_file=sources_file)
#     changetask(
#         ChangeLogEntry.objects.for_type(*models),
#         task=_export_data,
#         task_args=TaskArgs([], dict(target_file=target_file)),
#         task_name=task_name,
#         min_interval=min_interval,
#         refresh_interval=refresh_interval,
#         **kwargs,
#     )


# def _export_data(*args, target_file, **kwargs):
#     with TemporaryDirectory() as dirname:
#         output = Path(dirname) / "report.xlsx"
#         generate_report(output, report_file=report_file, sources_file=sources_file)
#         drive_response, filepart = api.parse_file_path(target_file)
#         api.upload_file(drive_response.value, filepart, output)


# @shared_task
# def export_review_documents(
#     target_file,
#     period=None,
#     task_name="EXPORT_REVIEW_DOCS",
#     min_interval=timedelta(minutes=5),
#     refresh_interval=timedelta(days=1),
#     **kwargs,
# ):

#     if period is None:
#         period = ReviewPeriod.objects.get_current()
#     else:
#         period = ReviewPeriod.objects.round(period)

#     saver = save_to_sharepoint(target_file)
#     changetask(
#         ChangeLogEntry.objects.for_type(ReviewFormResponse),
#         task=lambda: _export_review_documents(
#             Nomination.objects.filter(period=period), saver
#         ),
#         incremental_task=lambda qs: _export_review_documents(
#             Nomination.objects.filter(
#                 responses__in=qs.objects(ReviewFormResponse), period=period
#             ),
#             saver,
#         ),
#         task_name=task_name,
#         min_interval=min_interval,
#         refresh_interval=refresh_interval,
#         **kwargs,
#     )


# def _export_review_documents(queryset, saver):
#     try:
#         _export_single_reviews(queryset, saver)
#     except:
#         logger.exception("Failed to export single reviews")

#     try:
#         _export_grouped_reviews(queryset, saver)
#     except:
#         logger.exception("Failed to export grouped reviews")


# def _export_single_reviews(queryset, saver):
#     """
#     Export all reviews as single documents
#     :param queryset:
#     :param saver:
#     :return:
#     """
#     for nomination, path in export_nominations(queryset):
#         dir = f"{nomination.form.period}/responses/{nomination.reviewee.first_name} {nomination.reviewee.last_name}"
#         if nomination.role == ReviewerRole.ASSESSMENT_PT_1:
#             filename = f"{nomination.form.period} - {nomination.reviewee.first_name} {nomination.reviewee.last_name} - {nomination.form.title}.docx"
#         else:
#             filename = f"{nomination.reviewer_name} - {nomination.form.title}.docx"

#         try:
#             saver(path, dir, filename)
#         except:
#             logger.exception("Failed to save reviews for %s to %s", nomination, dir)


# def _export_grouped_reviews(queryset, saver):
#     """
#     Export all reviews, except for the assessments, as a single document per person
#     :param queryset:
#     :param saver:
#     :return:
#     """
#     for group in (
#         queryset.values("reviewee", "period").order_by("reviewee__username").distinct()
#     ):
#         for nom_info, path in export_grouped_nominations(
#             Nomination.objects.filter(
#                 ~Q(role=ReviewerRole.ASSESSMENT_PT_1.value),
#                 reviewee_id=group["reviewee"],
#                 period_id=group["period"],
#             ),
#             order_by="reviewee",
#         ):
#             nomination = nom_info["nominations"][0]
#             dir = f"{nomination.form.period}/responses/{nomination.reviewee.first_name} {nomination.reviewee.last_name}"
#             filename = f"{nomination.form.period} - {nomination.reviewee.first_name} {nomination.reviewee.last_name} - All Feedback.docx"
#             try:
#                 saver(path, dir, filename)
#             except:
#                 logger.exception("Failed to save reviews to %s", dir)
