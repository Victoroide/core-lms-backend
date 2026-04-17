from rest_framework import serializers

from apps.learning.models import Resource


class ResourceSerializer(serializers.ModelSerializer):
    """Serializer for Resource CRUD operations.

    Handles file uploads for lesson resources. The file field
    is backed by S3 via django-storages. The upload_to path
    is computed by the resource_upload_path callable.
    """

    class Meta:
        model = Resource
        fields = [
            "id",
            "lesson",
            "uploaded_by",
            "file",
            "resource_type",
            "title",
            "created_at",
        ]
        read_only_fields = ["id", "created_at"]
