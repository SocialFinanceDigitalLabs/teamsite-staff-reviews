from django.apps import AppConfig


class TeamsiteStaffReviewsConfig(AppConfig):
    name = "teamsite_staff_reviews"

    def ready(self):
        from teamsite_staff_reviews.tasks import export
