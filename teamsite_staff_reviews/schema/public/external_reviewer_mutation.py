import graphene
from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied
from django.db import transaction
from graphql_relay.connection.arrayconnection import offset_to_cursor

from teamsite_staff_reviews.util.graphql import get_id_from_type

from ...models import Nomination, ReviewFormQuestion, ReviewFormResponse
from .nodes import ReviewFormResponseNode

ReviewFormResponseEdge = ReviewFormResponseNode._meta.connection.Edge


class ExternalResponseUpdateMutation(graphene.relay.ClientIDMutation):
    response = graphene.Field(ReviewFormResponseNode)
    response_edge = graphene.Field(ReviewFormResponseEdge)

    class Input:
        nomination_id = graphene.ID(required=True)
        question_id = graphene.ID(required=True)
        value = graphene.String(required=True)

    @classmethod
    @transaction.atomic()
    def mutate_and_get_payload(cls, root, info, nomination_id, question_id, value):
        user = _get_user(info.context)
        try:
            nomination = Nomination.objects.get(
                pk=get_id_from_type(nomination_id, "ExternalReviewerNominationNode"),
                invitation__user=user,
            )
        except Nomination.DoesNotExist as ex:
            raise PermissionDenied("Only reviewer can submit for this question") from ex

        try:
            question = ReviewFormQuestion.objects.get(
                pk=get_id_from_type(question_id, "ReviewFormQuestionNode"),
                form__role=nomination.role,
            )
        except ReviewFormQuestion.DoesNotExist as ex:
            raise PermissionDenied(
                "Cannot find this question for this nomination"
            ) from ex

        response, _ = ReviewFormResponse.objects.update_or_create(
            nomination=nomination, question=question, defaults=dict(value=value)
        )

        if response.value != value:
            response.value = value
            response.save()

        edge = ReviewFormResponseEdge(cursor=offset_to_cursor(0), node=response)
        return ExternalResponseUpdateMutation(response=response, response_edge=edge)
