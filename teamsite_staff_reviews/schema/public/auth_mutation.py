import logging

import graphene
from django.core.validators import validate_email
from django.db import transaction
from django.template.loader import render_to_string
from django.utils.timezone import now

from ...models import ExternalInvitation, ExternalUser, ExternalUserToken

logger = logging.getLogger(__name__)


_SENDER = "kaj.siebert@socialfinance.org.uk"


class SendTokenMutation(graphene.Mutation):
    """
    Sends a token via email.

    Email only can be used in the following circumstances:
      * An External User already exists

    Email + Code can be used when
      * The Invitation Exists and is unclaimed
      * An External User may exist, or will be created if it doesn't

    """

    class Arguments:
        email = graphene.String(required=True)
        code = graphene.Int()

    ok = graphene.Boolean(required=True)

    @transaction.atomic
    def mutate(self, info, email, code=None):
        try:
            email = email.lower().strip()
            validate_email(email)
        except:
            logger.exception("Could not validate email & code combination")
            return SendTokenMutation(ok=False)

        token = ExternalUserToken.objects.create(email=email, code=code)

        msg_html = render_to_string(
            "reviews/redeem-token-email.html",
            {"url": f"https://feedback.sfdl.org.uk/#/key/{token.secret}"},
        )

        create_mail(
            mailbox=_SENDER,
            recipients=[token.email],
            subject="Social Finance Feedback Invitation",
            body=msg_html,
            send=True,
            save_to_sent=False,
        )

        return SendTokenMutation(ok=True)


class RedeemTokenMutation(graphene.Mutation):
    """
    Redeems a token
    """

    class Arguments:
        token = graphene.String(required=True)

    token = graphene.String(required=True)

    @transaction.atomic
    def mutate(self, info, token):
        try:
            # token = ExternalUserToken.objects.get(secret=token, redeemed__isnull=True)
            token = ExternalUserToken.objects.get(secret=token)
        except ExternalUserToken.DoesNotExist:
            raise ValueError("This token has already been used.")

        if token.expired:
            raise ValueError("This token has expired. Please request a new one.")

        if token.code is not None:
            invitation = ExternalInvitation.objects.get(code=token.code)

            user, created = ExternalUser.objects.get_or_create(email=token.email)

            if invitation.user is not None and invitation.user != user:
                raise ValueError("This invitation has already been claimed.")

            if invitation.user is None:
                invitation.user = user
                invitation.save()

        else:
            try:
                user = ExternalUser.objects.get(email=token.email)
            except ExternalUser.DoesNotExist:
                raise ValueError("You have no pending invitations.")

        jwt_token = SlidingToken.for_user(user)
        jwt_token["email"] = user.email

        token.redeemed = now()
        try:
            token.client_ip = get_ip(info.context)
        except:
            logger.exception("Failed to get user IP address")
        token.save()

        return RedeemTokenMutation(token=str(jwt_token))
