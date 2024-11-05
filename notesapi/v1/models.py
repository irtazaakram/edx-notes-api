from django.core.exceptions import ValidationError
from django.db import models


class Note(models.Model):
    """
    Annotation model.

    .. pii:: Stores 'text' and 'tags' about a particular course quote.
    .. pii_types:: other
    .. pii_retirement:: local_api, consumer_api
    """

    user_id = models.CharField(
        max_length=255, db_index=True, help_text="Anonymized user id, not course specific"
    )
    course_id = models.CharField(max_length=255, db_index=True)
    usage_id = models.CharField(max_length=255, help_text="ID of XBlock where the text comes from")
    quote = models.TextField(default="")
    text = models.TextField(default="", blank=True, help_text="Student's thoughts on the quote")
    ranges = models.JSONField(
        help_text="Describes position of quote in the source text", default=list
    )
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)
    tags = models.JSONField(help_text="list of comma-separated tags", default=list)

    @classmethod
    def create(cls, note_data):
        """
        Create the note object.
        """
        if not isinstance(note_data, dict):
            raise ValidationError("Note data must be a dictionary.")

        if not note_data:
            raise ValidationError("Note data cannot be empty.")

        ranges = note_data.get("ranges")
        if not ranges:
            raise ValidationError("Note must contain at least one range.")

        note_data["user_id"] = note_data.pop("user", None)
        return cls(**note_data)
