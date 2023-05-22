import graphene
from django.contrib.auth import get_user_model
from graphene import ConnectionField, ObjectType
from graphene_django import DjangoConnectionField, DjangoObjectType

from ...models import ReviewForm
from ..nodes import ReviewFormNode, ReviewFormResponseNode

User = get_user_model()


class ExternalUserNode(DjangoObjectType):
    class Meta:
        model = User
        interfaces = (graphene.relay.Node,)
        fields = (
            "first_name",
            "last_name",
        )


class ExternalReviewerNominationNode(ObjectType):
    reviewee = graphene.Field(ExternalUserNode)
    form = graphene.Field(ReviewFormNode)
    responses = DjangoConnectionField(ReviewFormResponseNode)

    @staticmethod
    def resolve_form(obj, info, **kwargs):
        return ReviewForm.objects.filter(period=obj.period, role=obj.role).first()

    class Meta:
        interfaces = (graphene.relay.Node,)


class ExternalReviewerNominationConnection(graphene.relay.Connection):
    class Meta:
        node = ExternalReviewerNominationNode


class ExternalReviewerNode(ObjectType):
    nominations = ConnectionField(ExternalReviewerNominationConnection)

    @staticmethod
    def resolve_nominations(obj, info, **kwargs):
        return [inv.nomination for inv in obj.invitations.all()]

    class Meta:
        interfaces = (graphene.relay.Node,)
