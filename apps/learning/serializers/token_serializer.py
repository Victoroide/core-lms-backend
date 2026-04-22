"""Custom JWT token serializer for AxiomLMS."""

from drf_yasg import openapi
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer


class AxiomTokenObtainPairSerializer(TokenObtainPairSerializer):
    """Custom standard JWT obtaining serialization object implementation logic.
    
    Extends TokenObtainPairSerializer to embed user-specific claims directly
    into the JWT payload and the response structure, supporting routing logic.
    """

    @classmethod
    def get_token(cls, user):
        """Construct the configuration JWT sequence mapped tokens for user generation.

        Args:
            user (LMSUser): The authentication verification payload identity target execution context object.

        Returns:
            Token: The fully constructed programmatic logic mapped output authorization entity sequence.
        """
        token = super().get_token(user)

        # Add custom claims into the JWT payload
        token["role"] = user.role
        token["vark_dominant"] = getattr(user, "vark_dominant", None)
        token["user_id"] = user.pk

        return token

    def validate(self, attrs):
        """Perform programmatic attribute validation execution against standard rules.

        Args:
            attrs (dict): The parameter request dictionary variable dictionary input mappings sequence.

        Returns:
            dict: The successful structural response containing embedded user dictionary configuration mapped keys.
        """
        data = super().validate(attrs)

        # Augment the response with a complete user object so the frontend does not need
        # to decode the JWT to understand role/profile logic parameters.
        data["user"] = {
            "id": self.user.pk,
            "username": self.user.get_username(),
            "email": self.user.email,
            "role": self.user.role,
            "vark_dominant": getattr(self.user, "vark_dominant", None),
            "full_name": self.user.get_full_name(),
        }

        return data
