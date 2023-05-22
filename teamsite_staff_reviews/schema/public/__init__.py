import graphene

from .auth_mutation import RedeemTokenMutation, SendTokenMutation
from .auth_query import AuthUserQuery
from .external_reviewer_mutation import ExternalResponseUpdateMutation
from .nodes import ExternalReviewerNode


def _get_user(context):
    raise NotImplementedError("TODO: implement this")


class Query:
    auth_user = graphene.Field(AuthUserQuery)
    my_reviews = graphene.Field(ExternalReviewerNode)

    @staticmethod
    def resolve_auth_user(obj, info, **kwargs):
        return _get_user(info.context)

    @staticmethod
    def resolve_my_reviews(obj, info, **kwargs):
        return _get_user(info.context)


class Mutation(graphene.ObjectType):
    send_token = SendTokenMutation.Field()
    redeem_token = RedeemTokenMutation.Field()
    update_review_response = ExternalResponseUpdateMutation.Field()
