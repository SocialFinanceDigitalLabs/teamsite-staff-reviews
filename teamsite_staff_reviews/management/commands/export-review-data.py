from django.core.management import BaseCommand
from resourcing.reports.complete.complete_export import generate_report, get_models
from reviews.tasks.export import report_file, sources_file


class Command(BaseCommand):
    help = """
    Exports review data
    """

    def add_arguments(self, parser):
        parser.add_argument("filename", nargs="?", type=str, default="reviews.xlsx")

    def handle(self, *args, filename, **options):
        models = get_models(report_file=report_file, sources_file=sources_file)
        print(models)
        generate_report(filename, report_file=report_file, sources_file=sources_file)
