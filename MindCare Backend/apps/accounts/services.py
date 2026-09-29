"""Write-path business logic for accounts.

Views call into these functions instead of touching the ORM or enforcing
business rules themselves. Anything that mutates state belongs here.
"""

from django.contrib.auth import authenticate
from django.db import IntegrityError, transaction
from django.utils.timezone import now

from apps.accounts.models import ApprovalStatus, Role, User
from apps.ngo.services import create_ngo_profile
from apps.patients.services import create_patient_profile
from apps.psychologists.services import create_psychologist_profile
from core.audit import log_auth_event
from core.exceptions import DomainValidationError

ROLES_REQUIRING_APPROVAL = {Role.PSYCHOLOGIST, Role.NGO}

# Direct calls, NOT signals: "every user has a profile, or neither exists" must
# be visible and testable (docs/decisions.md, 2026-09-26).
PROFILE_CREATORS = {
    Role.PATIENT: create_patient_profile,
    Role.PSYCHOLOGIST: create_psychologist_profile,
    Role.NGO: create_ngo_profile,
}


def register_user(
    *, email, password, full_name, role, is_adult_confirmed, profile_data
):
    if is_adult_confirmed is not True:
        raise DomainValidationError(
            {"is_adult_confirmed": ["You must confirm you are 18 or older."]}
        )
    email = email.lower()
    approval_status = (
        ApprovalStatus.PENDING
        if role in ROLES_REQUIRING_APPROVAL
        else ApprovalStatus.APPROVED
    )
    try:
        with transaction.atomic():
            user = User.objects.create_user(
                email=email,
                password=password,
                full_name=full_name,
                role=role,
                approval_status=approval_status,
                adult_confirmed_at=now(),
            )
            PROFILE_CREATORS[role](user=user, **profile_data)
    except IntegrityError as exc:
        if User.objects.filter(email__iexact=email).exists():
            raise DuplicateEmailError("A user with this email already exists.") from exc
        raise
    log_auth_event("register", user_id=user.id, email=user.email, role=user.role)
    return user


class InvalidCredentialsError(Exception):
    """Raised when email/password don't match an active account."""


class AccountPendingApprovalError(Exception):
    """Raised when a psychologist/NGO account hasn't been approved yet."""

    def __init__(self, message="Your account is pending admin approval."):
        super().__init__(message)


class AccountRejectedError(Exception):
    """Raised when a psychologist/NGO account's application was rejected."""

    def __init__(self, message="Your account application was not approved."):
        super().__init__(message)


class DuplicateEmailError(Exception):
    """Raised when a race lets two registrations for the same email past the serializer's pre-check."""


def authenticate_and_check_approval(*, email, password, ip=None):
    email = email.lower()
    user = authenticate(username=email, password=password)
    if user is None:
        log_auth_event("login_failed", email=email, ip=ip, success=False)
        raise InvalidCredentialsError(
            "No active account found with the given credentials"
        )

    if user.approval_status == ApprovalStatus.PENDING:
        log_auth_event(
            "login_failed",
            user_id=user.id,
            email=email,
            role=user.role,
            ip=ip,
            success=False,
        )
        raise AccountPendingApprovalError()

    if user.approval_status == ApprovalStatus.REJECTED:
        log_auth_event(
            "login_failed",
            user_id=user.id,
            email=email,
            role=user.role,
            ip=ip,
            success=False,
        )
        raise AccountRejectedError()

    log_auth_event("login", user_id=user.id, email=user.email, role=user.role, ip=ip)
    return user


def record_token_refresh(*, user, ip=None):
    log_auth_event(
        "token_refresh", user_id=user.id, email=user.email, role=user.role, ip=ip
    )


def record_logout(*, user, ip=None):
    log_auth_event("logout", user_id=user.id, email=user.email, role=user.role, ip=ip)
