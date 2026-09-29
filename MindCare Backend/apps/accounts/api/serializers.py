"""DRF serializers for the accounts API."""

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
    password = serializers.CharField(write_only=True, min_length=8)
    full_name = serializers.CharField(max_length=255)
    role = serializers.ChoiceField(choices=[Role.PATIENT, Role.PSYCHOLOGIST, Role.NGO])
    is_adult_confirmed = serializers.BooleanField(
        help_text="Must be true: the user declares they are 18 or older."
    )
    profile = serializers.DictField(
        help_text="Role-specific profile object; see API docs."
    )

    def validate_is_adult_confirmed(self, value):
        if value is not True:
            raise serializers.ValidationError("You must confirm you are 18 or older.")
        return value

    def validate(self, attrs):
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
        from django.contrib.auth.password_validation import (
            validate_password as django_validate_password,
        )
        from django.core.exceptions import ValidationError as DjangoValidationError

        try:
            django_validate_password(value)
        except DjangoValidationError as exc:
            raise serializers.ValidationError(list(exc.messages)) from exc
        return value


class UserPublicSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["id", "email", "full_name", "role", "approval_status"]


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
