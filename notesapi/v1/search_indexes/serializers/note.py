import json

from django_elasticsearch_dsl_drf.serializers import DocumentSerializer
from rest_framework import serializers

from ..documents import NoteDocument

__all__ = ("NoteDocumentSerializer",)


class NoteDocumentSerializer(DocumentSerializer):
    """
    Serializer for the Note document.
    """

    text = serializers.SerializerMethodField()
    ranges = serializers.SerializerMethodField()
    tags = serializers.SerializerMethodField()

    class Meta:
        """
        Meta options.
        """
        document = NoteDocument
        fields = (
            "id",
            "user",
            "course_id",
            "usage_id",
            "quote",
            "text",
            "ranges",
            "tags",
            "created",
            "updated",
        )

    def get_text(self, note):
        """
        Return note text.
        """
        return getattr(note.meta.highlight, "text", [note.text])[0]

    def get_ranges(self, note):
        """
        Return note ranges.
        """
        try:
            return json.loads(note.ranges)
        except (TypeError, json.JSONDecodeError):
            return []

    def get_tags(self, note):
        """
        Return note tags.
        """
        return getattr(note.meta.highlight, "tags", note.tags) or []
