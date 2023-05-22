import graphene
from django.contrib.auth import get_user_model
from graphene import ConnectionField, ObjectType
from graphene_django import DjangoConnectionField

from ..models import Nomination, ReviewForm
from .nodes import (
    NominationNode,
    NominationNodeIF,
    ReviewFormNode,
    ReviewFormResponseNode,
)

User = get_user_model()


class ReviewerNominationNodeIF(NominationNodeIF):
    responses = DjangoConnectionField(ReviewFormResponseNode)
    form = graphene.Field(ReviewFormNode)


class ReviewerNominationNode(NominationNode):
    @staticmethod
    def resolve_form(obj, info, **kwargs):
        return ReviewForm.objects.filter(period=obj.period, role=obj.role).first()

    class Meta:
        interfaces = (ReviewerNominationNodeIF,)
        fields = "__all__"
        model = Nomination


class ReviewerNominationConnection(graphene.relay.Connection):
    class Meta:
        node = ReviewerNominationNode


class ReviewerNode(ObjectType):
    nominations = ConnectionField(ReviewerNominationConnection)

    @staticmethod
    def resolve_nominations(obj, info, **kwargs):
        return obj.nominations.filter(reviewer=obj.user)

    class Meta:
        interfaces = (graphene.relay.Node,)
