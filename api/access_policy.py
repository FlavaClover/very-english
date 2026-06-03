from dataclasses import dataclass
from enum import Enum

from auth.models import UserRole


class RequiredSubscription(Enum):
    """Минимальный тариф подписки для доступа к маршруту."""

    BASE = "base"
    PRO = "pro"


@dataclass(frozen=True, slots=True)
class EndpointAccessRule:
    """Правило доступа к маршруту FastAPI (по шаблону path из APIRoute)."""

    method: str
    path: str
    require_jwt: bool
    role: UserRole | None = None
    required_subscription: RequiredSubscription | None = None


ENDPOINT_ACCESS_RULES: dict[tuple[str, str], EndpointAccessRule] = {
    ("POST", "/auth/register"): EndpointAccessRule(
        method="POST",
        path="/auth/register",
        require_jwt=False,
    ),
    ("POST", "/auth/register/tutor"): EndpointAccessRule(
        method="POST",
        path="/auth/register/tutor",
        require_jwt=False,
    ),
    ("POST", "/auth/login"): EndpointAccessRule(
        method="POST",
        path="/auth/login",
        require_jwt=False,
    ),
    ("POST", "/auth/refresh"): EndpointAccessRule(
        method="POST",
        path="/auth/refresh",
        require_jwt=False,
    ),
    ("GET", "/users/me"): EndpointAccessRule(
        method="GET",
        path="/users/me",
        require_jwt=True,
    ),
    ("GET", "/users/me/recent-tutor-profiles"): EndpointAccessRule(
        method="GET",
        path="/users/me/recent-tutor-profiles",
        require_jwt=True,
    ),
    ("PATCH", "/users/me"): EndpointAccessRule(
        method="PATCH",
        path="/users/me",
        require_jwt=True,
    ),
    ("POST", "/users/me/photo"): EndpointAccessRule(
        method="POST",
        path="/users/me/photo",
        require_jwt=True,
    ),
    ("DELETE", "/users/me/photo"): EndpointAccessRule(
        method="DELETE",
        path="/users/me/photo",
        require_jwt=True,
    ),
    ("PATCH", "/users/me/autopayment-consent"): EndpointAccessRule(
        method="PATCH",
        path="/users/me/autopayment-consent",
        require_jwt=True,
        role=UserRole.TUTOR,
    ),
    ("GET", "/subscriptions/plans"): EndpointAccessRule(
        method="GET",
        path="/subscriptions/plans",
        require_jwt=True,
        role=UserRole.TUTOR,
    ),
    ("GET", "/subscriptions/me"): EndpointAccessRule(
        method="GET",
        path="/subscriptions/me",
        require_jwt=True,
        role=UserRole.TUTOR,
    ),
    ("GET", "/subscriptions/me/history"): EndpointAccessRule(
        method="GET",
        path="/subscriptions/me/history",
        require_jwt=True,
        role=UserRole.TUTOR,
    ),
    ("GET", "/subscriptions/me/payments"): EndpointAccessRule(
        method="GET",
        path="/subscriptions/me/payments",
        require_jwt=True,
        role=UserRole.TUTOR,
    ),
    ("POST", "/subscriptions/checkout"): EndpointAccessRule(
        method="POST",
        path="/subscriptions/checkout",
        require_jwt=True,
        role=UserRole.TUTOR,
    ),
    ("POST", "/subscriptions/upgrade"): EndpointAccessRule(
        method="POST",
        path="/subscriptions/upgrade",
        require_jwt=True,
        role=UserRole.TUTOR,
    ),
    ("GET", "/subscriptions/me/upgrade/quote"): EndpointAccessRule(
        method="GET",
        path="/subscriptions/me/upgrade/quote",
        require_jwt=True,
        role=UserRole.TUTOR,
    ),
    ("POST", "/billing/webhooks/yookassa"): EndpointAccessRule(
        method="POST",
        path="/billing/webhooks/yookassa",
        require_jwt=False,
    ),
    ("GET", "/tags"): EndpointAccessRule(
        method="GET",
        path="/tags",
        require_jwt=True,
    ),
    ("POST", "/tags"): EndpointAccessRule(
        method="POST",
        path="/tags",
        require_jwt=True,
        role=UserRole.ADMIN,
    ),
    ("DELETE", "/tags/{tag_name}"): EndpointAccessRule(
        method="DELETE",
        path="/tags/{tag_name}",
        require_jwt=True,
        role=UserRole.ADMIN,
    ),
    ("GET", "/tutors"): EndpointAccessRule(
        method="GET",
        path="/tutors",
        require_jwt=True,
    ),
    ("GET", "/tutors/{tutor_id}"): EndpointAccessRule(
        method="GET",
        path="/tutors/{tutor_id}",
        require_jwt=True,
    ),
    ("POST", "/tutors/profile"): EndpointAccessRule(
        method="POST",
        path="/tutors/profile",
        require_jwt=True,
        role=UserRole.TUTOR,
    ),
    ("GET", "/tutors/me/profile"): EndpointAccessRule(
        method="GET",
        path="/tutors/me/profile",
        require_jwt=True,
        role=UserRole.TUTOR,
    ),
    ("PATCH", "/tutors/me/profile"): EndpointAccessRule(
        method="PATCH",
        path="/tutors/me/profile",
        require_jwt=True,
        role=UserRole.TUTOR,
        required_subscription=RequiredSubscription.BASE,
    ),
    ("POST", "/tutors/me/submit-moderation"): EndpointAccessRule(
        method="POST",
        path="/tutors/me/submit-moderation",
        require_jwt=True,
        role=UserRole.TUTOR,
        required_subscription=RequiredSubscription.BASE,
    ),
    ("POST", "/tutors/me/contacts"): EndpointAccessRule(
        method="POST",
        path="/tutors/me/contacts",
        require_jwt=True,
        role=UserRole.TUTOR,
        required_subscription=RequiredSubscription.BASE,
    ),
    ("DELETE", "/tutors/me/contacts/{contact_name}"): EndpointAccessRule(
        method="DELETE",
        path="/tutors/me/contacts/{contact_name}",
        require_jwt=True,
        role=UserRole.TUTOR,
        required_subscription=RequiredSubscription.BASE,
    ),
    ("POST", "/tutors/me/tags/{tag_name}"): EndpointAccessRule(
        method="POST",
        path="/tutors/me/tags/{tag_name}",
        require_jwt=True,
        role=UserRole.TUTOR,
        required_subscription=RequiredSubscription.BASE,
    ),
    ("DELETE", "/tutors/me/tags/{tag_name}"): EndpointAccessRule(
        method="DELETE",
        path="/tutors/me/tags/{tag_name}",
        require_jwt=True,
        role=UserRole.TUTOR,
        required_subscription=RequiredSubscription.BASE,
    ),
    ("POST", "/tutors/me/achievements"): EndpointAccessRule(
        method="POST",
        path="/tutors/me/achievements",
        require_jwt=True,
        role=UserRole.TUTOR,
        required_subscription=RequiredSubscription.BASE,
    ),
    ("DELETE", "/tutors/me/achievements/{achievement_name}"): EndpointAccessRule(
        method="DELETE",
        path="/tutors/me/achievements/{achievement_name}",
        require_jwt=True,
        role=UserRole.TUTOR,
        required_subscription=RequiredSubscription.BASE,
    ),
    ("POST", "/tutors/me/visit-video"): EndpointAccessRule(
        method="POST",
        path="/tutors/me/visit-video",
        require_jwt=True,
        role=UserRole.TUTOR,
        required_subscription=RequiredSubscription.PRO,
    ),
    ("POST", "/tutors/me/advantage"): EndpointAccessRule(
        method="POST",
        path="/tutors/me/advantage",
        require_jwt=True,
        role=UserRole.TUTOR,
        required_subscription=RequiredSubscription.PRO,
    ),
    ("DELETE", "/tutors/me/advantage"): EndpointAccessRule(
        method="DELETE",
        path="/tutors/me/advantage",
        require_jwt=True,
        role=UserRole.TUTOR,
        required_subscription=RequiredSubscription.PRO,
    ),
    ("GET", "/admin/tutors/moderation"): EndpointAccessRule(
        method="GET",
        path="/admin/tutors/moderation",
        require_jwt=True,
        role=UserRole.ADMIN,
    ),
    ("POST", "/admin/tutors/{tutor_id}/approve"): EndpointAccessRule(
        method="POST",
        path="/admin/tutors/{tutor_id}/approve",
        require_jwt=True,
        role=UserRole.ADMIN,
    ),
    ("POST", "/admin/tutors/{tutor_id}/reject"): EndpointAccessRule(
        method="POST",
        path="/admin/tutors/{tutor_id}/reject",
        require_jwt=True,
        role=UserRole.ADMIN,
    ),
}
