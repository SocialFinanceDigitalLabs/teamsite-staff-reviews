from datetime import timedelta

from django.db import transaction
from django.template.loader import render_to_string
from django.utils.timezone import now

from ..models import ExternalInvitationMessage

invite_personal_message = """
[This is an automatically generated message]

Dear %NAME%,

Thank you for agreeing to provide feedback on me for our review process. 

Below you will find a code and link to register and submit the feedback. I would be very grateful if you would do this before the deadline of %DEADLINE%. 

Thank you so much for your help. 

Best wishes,

%SENDER%
"""


@transaction.atomic()
def send_invite_email(nomination, message, from_user=None, action_user=None):
    if from_user is None:
        from_user = nomination.reviewee
    if action_user is None:
        action_user = nomination.reviewee

    if nomination.external_email is None:
        return ValueError("Email missing from nomination")

    name = f"{nomination.reviewee.first_name} {nomination.reviewee.last_name}"
    msg_html = render_to_string(
        "reviews/send-invite-email.html",
        {
            "url": f"https://feedback.sfdl.org.uk/#/login/?email={nomination.external_email}"
            f"&code={nomination.invitation.code}",
            "code": nomination.invitation.code,
            "message": message,
        },
    )

    last_message_sent = (
        ExternalInvitationMessage.objects.filter(invitation=nomination.invitation)
        .order_by("sent_time")
        .last()
    )

    if last_message_sent is not None and last_message_sent.sent_time > (
        now() - timedelta(minutes=30)
    ):
        return ValueError("Invitation was already sent less than 30 minutes ago.")

    ExternalInvitationMessage.objects.create(
        invitation=nomination.invitation,
        sent_to=nomination.external_email,
        sent_by=action_user,
        message=msg_html,
    )

    # TODO: Use standard django email sender
    create_mail(
        mailbox=from_user.email,
        recipients=[nomination.external_email],
        subject=f"Social Finance Feedback Invitation for {name}",
        body=msg_html,
        send=True,
        save_to_sent=True,
    )
