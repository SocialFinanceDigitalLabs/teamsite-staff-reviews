import graphene
from django.db.models.functions import Concat
from graphene import ObjectType
from graphene_django import DjangoConnectionField, DjangoObjectType

from ..models import (
    ExternalInvitation,
    ExternalInvitationMessage,
    Nomination,
    ReviewerRole,
    ReviewForm,
    ReviewFormQuestion,
    ReviewFormResponse,
    ReviewPeriod,
    ReviewRound,
    ReviewStage,
)


class ReviewStageNode(DjangoObjectType):
    class Meta:
        model = ReviewStage
        interfaces = (graphene.relay.Node,)
        fields = "__all__"


class NominationNodeIF(graphene.relay.Node):
    period = graphene.Field("reviews.schema.nodes.ReviewPeriodNode")
    reviewer = graphene.Field("resourcing.schema.user.UserNode")
    reviewee = graphene.Field("resourcing.schema.user.UserNode")
    role = graphene.String()
    role_label = graphene.String()
    form = graphene.Field("reviews.schema.nodes.ReviewFormNode")
    responses = DjangoConnectionField("reviews.schema.nodes.ReviewFormResponseNode")
    closes = graphene.DateTime()
    closes_override = graphene.DateTime()
    external_name = graphene.String()
    external_email = graphene.String()


class NominationNode(DjangoObjectType):
    @staticmethod
    def resolve_role_label(obj, info, **kwargs):
        return ReviewerRole(obj.role).label

    class Meta:
        model = Nomination
        fields = "__all__"
        interfaces = (NominationNodeIF,)


class LineReportNode(ObjectType):
    user = graphene.Field("resourcing.schema.user.UserNode")
    nominations = graphene.relay.ConnectionField(
        "reviews.schema.special_linemanager.LineManagerNominationConnection"
    )

    @staticmethod
    def resolve_user(obj, info, **kwargs):
        return obj

    @staticmethod
    def resolve_nominations(obj, info, **kwargs):
        return (
            Nomination.objects.filter(reviewee=obj, period_id=obj.period_id)
            .annotate(
                search_name=Concat(
                    "reviewer__first_name", "reviewer__last_name", "external_name"
                )
            )
            .order_by("search_name")
        )

    class Meta:
        interfaces = (graphene.relay.Node,)


class LineReportConnection(graphene.relay.Connection):
    class Meta:
        node = LineReportNode


class ReviewPeriodNode(DjangoObjectType):
    round_label = graphene.String()

    @staticmethod
    def resolve_round_label(obj, info, **kwargs):
        return ReviewRound(obj.round).label

    class Meta:
        model = ReviewPeriod
        interfaces = (graphene.relay.Node,)
        fields = ("year", "round", "round_label")


class ReviewFormQuestionNode(DjangoObjectType):
    class Meta:
        model = ReviewFormQuestion
        interfaces = (graphene.relay.Node,)
        fields = ("form", "sequence", "title", "description")


class ReviewFormResponseNode(DjangoObjectType):
    class Meta:
        model = ReviewFormResponse
        interfaces = (graphene.relay.Node,)
        fields = "__all__"


class ReviewFormNode(DjangoObjectType):
    role_label = graphene.String()

    @staticmethod
    def resolve_role_label(obj, info, **kwargs):
        return ReviewerRole(obj.role).label

    class Meta:
        model = ReviewForm
        interfaces = (graphene.relay.Node,)
        fields = "__all__"


class ExternalInvitationNode(DjangoObjectType):
    last_sent = graphene.DateTime()

    @staticmethod
    def resolve_last_sent(obj, info, **kwargs):
        last = obj.messages.order_by("sent_time").last()
        if last is None:
            return None
        else:
            return last.sent_time

    class Meta:
        model = ExternalInvitation
        interfaces = (graphene.relay.Node,)
        fields = ("code", "messages")


class ExternalInvitationMessageNode(DjangoObjectType):
    class Meta:
        model = ExternalInvitationMessage
        interfaces = (graphene.relay.Node,)
        fields = "__all__"
