from datetime import timedelta

from admin_auto_filters.filters import AutocompleteFilterFactory
from dateutil.relativedelta import MO, relativedelta
from django.contrib import admin
from django.contrib.admin import SimpleListFilter
from django.db.models import Count
from django.db.models.functions import Concat, Length
from django.utils import timezone

from .models import (
    ExternalInvitation,
    ExternalInvitationMessage,
    ExternalNomination,
    ExternalUser,
    ExternalUserToken,
    Nomination,
    ReviewerRole,
    ReviewForm,
    ReviewFormQuestion,
    ReviewFormResponse,
    ReviewPeriod,
    ReviewStage,
    StageCode,
)
from .util.email_sender import invite_personal_message, send_invite_email


class ReviewStageInline(admin.StackedInline):
    model = ReviewStage
    fields = [
        "date",
        "code",
        "title",
        "description",
        "configuration",
        "visible",
    ]
    extra = 0
    show_change_link = True

    def get_readonly_fields(self, request, obj=None):
        if request.user.is_superuser:
            return tuple()
        else:
            return ("configuration",)


class ReviewFormInline(admin.StackedInline):
    model = ReviewForm
    fields = [
        "role",
        "title",
        "description",
    ]
    extra = 0
    show_change_link = True


@admin.register(ReviewPeriod)
class ReviewPeriodAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "year",
        "round",
        "stages_count",
        "form_count",
    )
    inlines = (ReviewStageInline, ReviewFormInline)
    actions = ["add_default_stages", "add_forms", "nominate_line_managers"]

    def name(self, obj):
        return str(obj)

    @admin.display(description="# Stages")
    def stages_count(self, obj):
        return obj.stages.count()

    @admin.display(description="# Forms")
    def form_count(self, obj):
        return obj.forms.count()

    @admin.action(description="Add default stages")
    def add_default_stages(self, request, queryset):
        for period in queryset:
            period.add_default_stages()

    @admin.action(description="Add forms")
    def add_forms(self, request, queryset):
        for period in queryset:
            period.add_forms()

    @admin.action(description="Nominate Line Managers")
    def nominate_line_managers(self, request, queryset):
        for period in queryset:
            period.nominate_line_managers()


class PeriodFilter(SimpleListFilter):
    title = "period"
    parameter_name = "period"

    def lookups(self, request, model_admin):
        return [(p.id, str(p)) for p in ReviewPeriod.objects.all()]

    def queryset(self, request, queryset):
        value = self.value()
        if value is not None:
            return queryset.filter(period_id=value)


@admin.register(Nomination)
class NominationAdmin(admin.ModelAdmin):
    list_display = (
        "desc",
        "period",
        "reviewee",
        "reviewer",
        "role",
        "closes_override",
        "get_responses",
    )
    list_filter = (
        PeriodFilter,
        AutocompleteFilterFactory("reviewee", "reviewee"),
        AutocompleteFilterFactory("reviewer", "reviewer"),
        "role",
    )
    search_fields = ("reviewee__email", "reviewer__email", "external_email")

    def desc(self, obj):
        return str(obj)

    def get_responses(self, obj):
        return obj.response_count

    get_responses.short_description = "Response Count"
    get_responses.admin_order_field = "response_count"

    def get_queryset(self, request):
        qs = super(NominationAdmin, self).get_queryset(request)
        return qs.annotate(response_count=Count("responses"))


class ReviewFormQuestionInline(admin.TabularInline):
    model = ReviewFormQuestion
    fields = ("sequence", "title", "description")
    extra = 0


@admin.register(ReviewForm)
class ReviewFormAdmin(admin.ModelAdmin):
    list_display = ("period", "role", "description")
    list_filter = ("period", "role")
    inlines = (ReviewFormQuestionInline,)


@admin.register(ReviewFormResponse)
class ReviewFormResponseAdmin(admin.ModelAdmin):
    list_display = (
        "get_review_form",
        "get_question",
        "reviewer",
        "reviewee",
        "role",
        "answer_length",
    )
    list_filter = (
        "question__form__period",
        "question__form__title",
        AutocompleteFilterFactory("reviewee", "nomination__reviewee"),
        AutocompleteFilterFactory("internal reviewer", "nomination__reviewer"),
    )
    search_fields = (
        "question__form__title",
        "nomination__reviewee__username",
        "nomination__reviewer__username",
        "nomination__invitation__user__email",
    )
    readonly_fields = ("nomination", "question")

    def get_review_form(self, obj):
        return obj.question.form.title

    get_review_form.short_description = "form"
    get_review_form.admin_order_field = "question__form__title"

    def get_question(self, obj):
        return obj.question.sequence

    get_question.short_description = "question"
    get_question.admin_order_field = "question__sequence"

    def question_title(self, obj):
        return f"{obj.question.title}"

    question_title.admin_order_field = "question__title"

    def reviewer(self, obj):
        try:
            return f"{obj.nomination.reviewer.profile.short_name}"
        except AttributeError:
            return f"{obj.nomination.invitation.user.email}"

    reviewer.admin_order_field = Concat(
        "nomination__reviewer__profile__short_name",
        "nomination__invitation__user__email",
    )

    def reviewee(self, obj):
        return f"{obj.nomination.reviewee.profile.short_name}"

    reviewee.admin_order_field = "nomination__reviewee__profile__short_name"

    def role(self, obj):
        return f"{ReviewerRole(obj.nomination.role).label}"

    role.admin_order_field = "nomination__role"

    def period(self, obj):
        return f"{obj.nomination.period}"

    period.admin_order_field = "nomination__period"

    def answer_length(self, obj):
        return f"{len(obj.value)}"

    answer_length.admin_order_field = Length("value")


@admin.register(ExternalUser)
class ExternalUserAdmin(admin.ModelAdmin):
    list_display = ("email", "name", "failure_count", "is_enabled")


@admin.register(ExternalInvitation)
class ExternalInvitationAdmin(admin.ModelAdmin):
    list_display = ("invitation_from", "invitation_to", "user", "code")
    autocomplete_fields = ("nomination",)

    def invitation_from(self, obj):
        return obj.nomination.reviewee.profile.short_name

    invitation_from.admin_order_field = "nomination__reviewee__profile__short_name"

    def invitation_to(self, obj):
        if obj.nomination.external_email:
            return obj.nomination.external_email
        else:
            return obj.nomination.reviewer.profile.short_name

    invitation_to.admin_order_field = Concat(
        "nomination__external_email", "nomination__reviewer__profile__short_name"
    )


@admin.register(ExternalInvitationMessage)
class ExternalInvitationMessageAdmin(admin.ModelAdmin):
    list_display = ("invitation_from", "linked_by", "sent_time", "sent_to", "sent_by")

    def invitation_from(self, obj):
        return obj.invitation.nomination.reviewee.profile.short_name

    def linked_by(self, obj):
        return obj.invitation.user


@admin.register(ExternalUserToken)
class ExternalUserTokenAdmin(admin.ModelAdmin):
    list_display = ("email", "short_secret", "expiry", "redeemed", "client_ip")

    def short_secret(self, obj):
        return f"{obj.secret[:10]}..."


def create_invitation(modeladmin, request, queryset):
    for nom in queryset:
        ExternalInvitation.objects.get_or_create(nomination=nom)


create_invitation.short_description = "Create Invitation"


def send_invitation(modeladmin, request, queryset):
    for nom in queryset:
        closes = nom.closes
        message = invite_personal_message
        message = message.replace("%NAME%", nom.external_name)
        message = message.replace("%SENDER%", nom.reviewee.first_name)
        message = message.replace("%DEADLINE%", f"{closes:%B} {closes.day}")
        send_invite_email(nom, message, action_user=request.user)


send_invitation.short_description = "Send Invitation"


@admin.register(ExternalNomination)
class ExternalNominationAdmin(admin.ModelAdmin):
    list_display = (
        "desc",
        "period",
        "reviewee",
        "external_email",
        "get_invitation",
        "get_invitation_message_count",
        "get_invitation_user",
        "closes_override",
        "get_responses",
    )
    list_filter = (
        PeriodFilter,
        AutocompleteFilterFactory("reviewee", "reviewee"),
    )
    search_fields = ("external_email", "reviewee__username", "invitation__user__email")
    actions = [create_invitation, send_invitation]

    def desc(self, obj):
        return str(obj)

    def get_invitation(self, obj):
        return obj.invitation is not None

    get_invitation.boolean = True
    get_invitation.short_description = "Invitation"

    def get_invitation_message_count(self, obj):
        if obj.invitation:
            return obj.invitation.messages.count()

    get_invitation_message_count.short_description = "Messages Sent"

    def get_invitation_user(self, obj):
        if obj.invitation and obj.invitation.user:
            return obj.invitation.user.email

    get_invitation_user.short_description = "Invitation Accepted"

    def get_responses(self, obj):
        return obj.response_count

    get_responses.short_description = "Response Count"
    get_responses.admin_order_field = "response_count"

    def get_queryset(self, request):
        qs = (
            super(ExternalNominationAdmin, self)
            .get_queryset(request)
            .filter(role=ReviewerRole.EXTERNAL)
        )
        return qs.annotate(response_count=Count("responses"))
