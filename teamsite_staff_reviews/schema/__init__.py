import graphene
from django.utils.timezone import now

from ..models import ReviewStage
from .nomination_mutation import NominationCreateMutation, NominationDeleteMutation
from .review_cycle import ReviewCycleNode
from .reviewer_mutation import ExternalSendMutation, ResponseUpdateMutation


class Query(object):
    current_review_cycle = graphene.Field(ReviewCycleNode)

    @staticmethod
    def resolve_current_review_cycle(obj, info, **kwargs):
        stage = (
            ReviewStage.objects.filter(
                code="OPEN",
                date__lte=now(),
            )
            .order_by("-date")
            .first()
        )
        if stage is None:
            return None

        stage.period.user = info.context.user
        return stage.period


class Mutation(graphene.ObjectType):
    create_nomination = NominationCreateMutation.Field()
    delete_nomination = NominationDeleteMutation.Field()
    update_review_response = ResponseUpdateMutation.Field()
    send_external = ExternalSendMutation.Field()
