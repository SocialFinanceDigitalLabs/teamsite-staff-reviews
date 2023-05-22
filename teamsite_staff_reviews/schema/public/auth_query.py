import graphene
from graphene_django import DjangoObjectType

from ...models import ExternalUser


class AuthUserQuery(DjangoObjectType):
    class Meta:
        model = ExternalUser
        interfaces = (graphene.relay.Node,)
        fields = ("email",)
