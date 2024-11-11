import json

from rest_framework import serializers

__all__ = (
    'NoteDocumentSerializer',
)


class NoteDocumentSerializer(serializers.Serializer):  # pylint: disable=abstract-method
    """
    Serializer for the Note document.
    """

    id = serializers.CharField()
    user = serializers.CharField()
    course_id = serializers.CharField()
    usage_id = serializers.CharField()
    quote = serializers.CharField()
    created = serializers.DateTimeField()
    updated = serializers.DateTimeField()
    text = serializers.SerializerMethodField()
    ranges = serializers.SerializerMethodField()
    tags = serializers.SerializerMethodField()

    def get_text(self, note):
        """
        Return note text with highlighting if present.
        """
        if hasattr(note.meta, 'highlight') and 'text' in note.meta.highlight:
            return note.meta.highlight['text'][0]
        return note.text

    def get_ranges(self, note):
        """
        Return note ranges as JSON.
        """
        return json.loads(note.ranges)

    def get_tags(self, note):
        """
        Return note tags with highlighting if present.
        """
        if hasattr(note.meta, 'highlight') and 'tags' in note.meta.highlight:
            return list(note.meta.highlight['tags'])
        return list(note.tags) if note.tags else []
