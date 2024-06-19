from rest_framework import serializers

from ...models import ContentType


class ContentTypeBaseSerializer(serializers.ModelSerializer):
    class Meta:
        model = ContentType
        fields = [
            "id",
            "type_name",
            "name",
            "name_sv",
            "name_en",
        ]


class ContentTypeSerializer(ContentTypeBaseSerializer):
    class Meta:
        model = ContentTypeBaseSerializer.Meta.model
        fields = ContentTypeBaseSerializer.Meta.fields + [
            "description",
            "description_sv",
            "description_en",
        ]
