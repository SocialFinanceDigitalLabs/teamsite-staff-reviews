from datetime import timedelta

import graphene
from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.utils.timezone import now
from graphql_relay import from_global_id
from graphql_relay.connection.arrayconnection import offset_to_cursor

from ..models import Nomination, ReviewFormQuestion, ReviewFormResponse
from ..util.email_sender import send_invite_email
from ..util.graphql import get_id_from_type
from .nodes import ReviewFormResponseNode

User = get_user_model()

ReviewFormResponseEdge = ReviewFormResponseNode._meta.connection.Edge


class ResponseUpdateMutation(graphene.relay.ClientIDMutation):
    response = graphene.Field(ReviewFormResponseNode)
    response_edge = graphene.Field(ReviewFormResponseEdge)

    class Input:
        nomination_id = graphene.ID(required=True)
        question_id = graphene.ID(required=True)
        value = graphene.String(required=True)

    @classmethod
    @transaction.atomic()
    def mutate_and_get_payload(cls, root, info, nomination_id, question_id, value):
        user = info.context.user
        _type, _id = from_global_id(nomination_id)
        try:
            nomination = Nomination.objects.get(pk=_id, reviewer=user)
        except Nomination.DoesNotExist as ex:
            raise PermissionDenied("Only reviewer can submit for this question") from ex

        if nomination.closes < now():
            raise PermissionDenied("This nomination is now closed for submissions.")

        try:
            question = ReviewFormQuestion.objects.get(
                pk=get_id_from_type(question_id, "ReviewFormQuestionNode"),
                form__role=nomination.role,
            )
        except ReviewFormQuestion.DoesNotExist as ex:
            raise PermissionDenied(
                "Cannot find this question for this nomination"
            ) from ex

        response, created = ReviewFormResponse.objects.update_or_create(
            nomination=nomination, question=question, defaults=dict(value=value)
        )

        if response.value != value:
            response.value = value
            response.save()

        edge = ReviewFormResponseEdge(cursor=offset_to_cursor(0), node=response)
        return ResponseUpdateMutation(response=response, response_edge=edge)


class ExternalSendMutation(graphene.Mutation):
    class Arguments:
        nomination_id = graphene.ID(required=True)
        message = graphene.String(required=True)

    ok = graphene.Boolean(required=True)
    message = graphene.String()

    @transaction.atomic()
    def mutate(self, info, nomination_id, message):
        user = info.context.user
        try:
            nomination = Nomination.objects.get(
                pk=get_id_from_type(nomination_id, "NominationNode"), reviewee=user
            )
        except Nomination.DoesNotExist as ex:
            return ExternalSendMutation(
                ok=False, message="Only reviewee can send the invitation"
            )

        try:
            send_invite_email(nomination, message, action_user=user)
        except ValueError as ex:
            return ExternalSendMutation(ok=False, message=ex.args[0])

        return ExternalSendMutation(ok=True)
