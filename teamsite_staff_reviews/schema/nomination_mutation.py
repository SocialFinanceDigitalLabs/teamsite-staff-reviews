import graphene
from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied
from django.db import transaction
from graphql_relay.connection.arrayconnection import offset_to_cursor

from ..models import Nomination, ReviewerRole
from ..util.graphql import get_id_from_type
from .nodes import NominationNode
from .review_cycle import ReviewCycleNode

User = get_user_model()

NominationEdge = NominationNode._meta.connection.Edge


class NominationCreateMutation(graphene.relay.ClientIDMutation):
    nomination = graphene.Field(NominationNode)
    nomination_edge = graphene.Field(NominationEdge)

    class Input:
        value = graphene.String(required=True)
        role = graphene.String(required=True)
        name = graphene.String(required=False)

    @classmethod
    @transaction.atomic()
    def mutate_and_get_payload(cls, root, info, value, role, name=None):
        from . import Query

        period = Query.resolve_current_review_cycle(root, info)
        if period is None:
            raise ValueError("No current review cycle")

        stage = ReviewCycleNode.resolve_current_stage(period, info)
        if stage.code != "NOMINATIONS":
            raise ValueError("Not currently accepting nominations")

        user = period.user

        role = ReviewerRole(role)

        if role == ReviewerRole.EXTERNAL:
            nom, created = Nomination.objects.update_or_create(
                period=period,
                reviewee=user,
                external_email=value,
                defaults={"role": role},
            )
            nom.role = role
            nom.external_name = name
            nom.save()
        else:
            nom, created = Nomination.objects.update_or_create(
                period=period,
                reviewee=user,
                reviewer=User.objects.get(username=value),
                defaults={"role": role},
            )
            nom.role = role
            nom.save()

        edge = NominationEdge(cursor=offset_to_cursor(0), node=nom)
        return NominationCreateMutation(nomination=nom, nomination_edge=edge)


class NominationDeleteMutation(graphene.relay.ClientIDMutation):
    deleted_nomination_id = graphene.ID()

    class Input:
        id = graphene.ID(required=True)

    @classmethod
    @transaction.atomic()
    def mutate_and_get_payload(cls, root, info, id):
        from . import Query

        period = Query.resolve_current_review_cycle(root, info)
        if period is None:
            raise ValueError("No current review cycle")

        stage = ReviewCycleNode.resolve_current_stage(period, info)
        if stage.code != "NOMINATIONS":
            raise ValueError("Not currently accepting nominations")

        user = period.user
        try:
            nom = Nomination.objects.get(
                pk=get_id_from_type(id, "NominationNode"), reviewee=user
            )
        except Nomination.DoesNotExist as ex:
            raise PermissionDenied("Only reviewee can delete nomination") from ex

        nom.delete()

        return NominationDeleteMutation(deleted_nomination_id=id)
