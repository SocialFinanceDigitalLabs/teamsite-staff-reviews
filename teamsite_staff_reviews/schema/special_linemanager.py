import graphene
from django.contrib.auth import get_user_model
from django_celery_beat.utils import now

from ..models import Nomination
from .special_reviewer import ReviewerNominationNode, ReviewerNominationNodeIF

User = get_user_model()


class LineManagerNominationNode(ReviewerNominationNode):
    @staticmethod
    def resolve_responses(obj, info, **kwargs):
        user = info.context.user
        if obj.closes > now() and obj.reviewer != user:
            return []
        else:
            return obj.responses

    class Meta:
        interfaces = (ReviewerNominationNodeIF,)
        model = Nomination
        fields = "__all__"


class LineManagerNominationConnection(graphene.relay.Connection):
    class Meta:
        node = LineManagerNominationNode
