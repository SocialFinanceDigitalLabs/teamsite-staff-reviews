import graphene
from django.contrib.auth import get_user_model
from django.db.models import IntegerField, Q, Value
from django.utils.timezone import now
from graphene import ObjectType
from graphene_django import DjangoConnectionField

from .nodes import (
    LineReportConnection,
    NominationNode,
    ReviewFormNode,
    ReviewPeriodNode,
    ReviewStageNode,
)
from .special_reviewer import ReviewerNode

User = get_user_model()


class ReviewCycleNode(ObjectType):
    period = graphene.Field(ReviewPeriodNode)
    stages = DjangoConnectionField(ReviewStageNode)
    current_stage = graphene.Field(ReviewStageNode)
    nominations = DjangoConnectionField(NominationNode)
    to_review = DjangoConnectionField(NominationNode)
    line_reports = graphene.relay.ConnectionField(LineReportConnection)
    forms = DjangoConnectionField(ReviewFormNode)
    reviewer_view = graphene.Field(ReviewerNode)
    external_invites = DjangoConnectionField(NominationNode)

    @staticmethod
    def resolve_id(obj, info, **kwargs):
        return "current"

    @staticmethod
    def resolve_reviewer_view(obj, info, **kwargs):
        return obj

    @staticmethod
    def resolve_period(obj, info, **kwargs):
        return obj

    @staticmethod
    def resolve_current_stage(obj, info, **kwargs):
        return obj.stages.filter(date__lte=now()).order_by("-date").first()

    @staticmethod
    def resolve_nominations(obj, info, **kwargs):
        return obj.nominations.filter(reviewee=obj.user)

    @staticmethod
    def resolve_to_review(obj, info, **kwargs):
        return obj.nominations.filter(reviewer=obj.user)

    @staticmethod
    def resolve_external_invites(obj, info, **kwargs):
        return obj.nominations.filter(reviewee=obj.user, invitation__isnull=False)

    @staticmethod
    def resolve_line_reports(obj, info, **kwargs):
        return (
            User.objects.filter(
                Q(profile__end_date__isnull=True) | Q(profile__end_date__gte=now()),
                profile__line_manager=obj.user,
            )
            .annotate(period_id=Value(obj.pk, output_field=IntegerField()))
            .order_by("first_name", "last_name")
        )

    class Meta:
        interfaces = (graphene.relay.Node,)
