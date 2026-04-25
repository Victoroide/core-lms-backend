"""Custom JWT token serializer for AxiomLMS."""

from rest_framework_simplejwt.serializers import TokenObtainPairSerializer


class AxiomTokenObtainPairSerializer(TokenObtainPairSerializer):
    """Custom JWT serializer that embeds extra LMS-specific claims.

    Extends TokenObtainPairSerializer to embed user-specific claims directly
    into the JWT payload and the response structure, supporting routing logic.
    """

    @classmethod
    def get_token(cls, user):
        """Build the JWT for ``user`` with role/profile claims embedded.

        Args:
            user (LMSUser): The authenticated user.

        Returns:
            Token: The JWT with custom claims attached.
        """
        token = super().get_token(user)

        # Add custom claims into the JWT payload
        token["role"] = user.role
        token["vark_dominant"] = getattr(user, "vark_dominant", None)
        token["user_id"] = user.pk

        return token

    def validate(self, attrs):
        """Validate credentials and augment the response with a user object.

        Args:
            attrs (dict): The credential payload submitted by the client.

        Returns:
            dict: The token response augmented with a nested ``user`` dict.
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
