"""DRF serializers for the accounts API."""

from django.contrib.auth.password_validation import (
    validate_password as django_validate_password,
)
from django.core.exceptions import ValidationError as DjangoValidationError
from drf_spectacular.utils import PolymorphicProxySerializer
from rest_framework import serializers
from rest_framework.exceptions import AuthenticationFailed
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

from apps.accounts import services
from apps.accounts.models import Role, User
from apps.ngo.api.serializers import (
    NGOProfileOwnerSerializer,
    NGORegistrationProfileSerializer,
)
from apps.patients.api.serializers import (
    PatientProfileOwnerSerializer,
    PatientRegistrationProfileSerializer,
)
from apps.psychologists.api.serializers import (
    PsychologistProfileOwnerSerializer,
    PsychologistRegistrationProfileSerializer,
)
from core.serializers import StrictTrueField, person_name_field

ADULT_CONFIRMATION_ERROR = "You must confirm you are 18 or older."

# role -> (registration input serializer, owner output serializer, User reverse accessor)
PROFILE_SERIALIZERS = {
    Role.PATIENT: (
        PatientRegistrationProfileSerializer,
        PatientProfileOwnerSerializer,
        "patient_profile",
    ),
    Role.PSYCHOLOGIST: (
        PsychologistRegistrationProfileSerializer,
        PsychologistProfileOwnerSerializer,
        "psychologist_profile",
    ),
    Role.NGO: (
        NGORegistrationProfileSerializer,
        NGOProfileOwnerSerializer,
        "ngo_profile",
    ),
}


class RegisterSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True, trim_whitespace=False)
    full_name = person_name_field("Full name")
    role = serializers.ChoiceField(choices=[Role.PATIENT, Role.PSYCHOLOGIST, Role.NGO])
    is_adult_confirmed = StrictTrueField(
        help_text="Must be the JSON boolean true: the user declares they are 18 or older.",
        error_messages={
            "invalid": ADULT_CONFIRMATION_ERROR,
            "required": ADULT_CONFIRMATION_ERROR,
            "null": ADULT_CONFIRMATION_ERROR,
        },
    )
    profile = serializers.DictField(
        help_text="Role-specific profile object; see API docs."
    )

    def validate(self, attrs):
        # Django's password validators, with the user's own details so "too
        # similar to the email / full name" is checked (validation-rules.md).
        _validate_password_for(
            attrs["password"], email=attrs["email"], full_name=attrs["full_name"]
        )
        input_serializer_class = PROFILE_SERIALIZERS[attrs["role"]][0]
        profile = input_serializer_class(data=attrs["profile"])
        if not profile.is_valid():
            raise serializers.ValidationError({"profile": profile.errors})
        attrs["profile"] = profile.validated_data
        return attrs

    def validate_email(self, value):
        if User.objects.filter(email__iexact=value).exists():
            raise serializers.ValidationError("A user with this email already exists.")
        return value

    def validate_password(self, value):
        # Without user details first, so a weak password is reported even when
        # another field is invalid too; similarity is checked in validate().
        messages = _password_problems(value)
        if messages:
            raise serializers.ValidationError(messages)
        return value


def _password_problems(password, *, email=None, full_name=None):
    user = User(email=email, full_name=full_name) if email else None
    try:
        django_validate_password(password, user=user)
    except DjangoValidationError as exc:
        return list(exc.messages)
    return []


def _validate_password_for(password, *, email, full_name):
    messages = _password_problems(password, email=email, full_name=full_name)
    if messages:
        raise serializers.ValidationError({"password": messages})


class UserPublicSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["id", "email", "full_name", "role", "approval_status"]


# --- Documentation-only serializers (OpenAPI). The view validates with
# RegisterSerializer; these only describe the per-role request/response shapes.
def _register_request_serializer(role, profile_serializer_class):
    fields = {
        "email": serializers.EmailField(),
        "password": serializers.CharField(min_length=8),
        "full_name": serializers.CharField(max_length=255),
        "role": serializers.CharField(help_text=f"Always '{role}'."),
        "is_adult_confirmed": serializers.BooleanField(
            help_text="Must be the JSON boolean true."
        ),
        "profile": profile_serializer_class(),
    }
    return type(f"{role.title()}RegisterRequest", (serializers.Serializer,), fields)


def _register_response_serializer(role, owner_serializer_class):
    meta = type(
        "Meta",
        (UserPublicSerializer.Meta,),
        {"fields": [*UserPublicSerializer.Meta.fields, "profile"]},
    )
    fields = {
        "role": serializers.CharField(help_text=f"Always '{role}'."),
        "profile": owner_serializer_class(),
        "Meta": meta,
    }
    return type(f"{role.title()}RegisterResponse", (UserPublicSerializer,), fields)


RegisterRequestDoc = PolymorphicProxySerializer(
    component_name="RegisterRequest",
    serializers={
        role.value: _register_request_serializer(role.value, input_cls)
        for role, (input_cls, _, _) in PROFILE_SERIALIZERS.items()
    },
    resource_type_field_name="role",
)

RegisterResponseDoc = PolymorphicProxySerializer(
    component_name="RegisterResponse",
    serializers={
        role.value: _register_response_serializer(role.value, owner_cls)
        for role, (_, owner_cls, _) in PROFILE_SERIALIZERS.items()
    },
    resource_type_field_name="role",
)


def registration_response_data(user):
    _, owner_serializer_class, accessor = PROFILE_SERIALIZERS[user.role]
    data = dict(UserPublicSerializer(user).data)
    data["profile"] = owner_serializer_class(getattr(user, accessor)).data
    return data


class MindCareTokenObtainPairSerializer(TokenObtainPairSerializer):
    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        token["role"] = user.role
        return token

    def validate(self, attrs):
        request = self.context.get("request")
        ip = request.META.get("REMOTE_ADDR") if request is not None else None

        try:
            user = services.authenticate_and_check_approval(
                email=attrs[self.username_field], password=attrs["password"], ip=ip
            )
        except services.InvalidCredentialsError as exc:
            raise AuthenticationFailed(str(exc), code="no_active_account") from exc
        except services.AccountPendingApprovalError as exc:
            raise AuthenticationFailed(
                str(exc), code="account_pending_approval"
            ) from exc
        except services.AccountRejectedError as exc:
            raise AuthenticationFailed(str(exc), code="account_rejected") from exc

        refresh = self.get_token(user)
        return {"refresh": str(refresh), "access": str(refresh.access_token)}
