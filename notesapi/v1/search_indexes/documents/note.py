import json
import logging

from django.conf import settings
from django_elasticsearch_dsl import Document, Index, fields

from notesapi.v1.models import Note

from .analyzers import case_insensitive_keyword, html_strip

log = logging.getLogger(__name__)

__all__ = ("NoteDocument",)

NOTE_INDEX = Index(settings.ELASTICSEARCH_INDEX_NAMES.get(__name__))

@NOTE_INDEX.document
class NoteDocument(Document):
    """
    Document for the Note index.
    """

    id = fields.IntegerField(attr="id")
    user = fields.KeywordField(attr="user_id")
    course_id = fields.KeywordField()
    usage_id = fields.KeywordField()
    quote = fields.TextField(analyzer=html_strip)
    text = fields.TextField(analyzer=html_strip)
    ranges = fields.KeywordField()
    created = fields.DateField()
    updated = fields.DateField()
    tags = fields.TextField(multi=True, analyzer=case_insensitive_keyword)

    def prepare_data(self, instance):
        """
        Prepare data.
        """
        return f"{instance.text} {instance.tags}"

    def prepare_tags(self, instance):
        try:
            return json.loads(instance.tags) if instance.tags else []
        except json.JSONDecodeError as exc:
            log.warning(
                "Field `tags` contains invalid JSON data. Data: %r. Exception: %r",
                instance.tags, exc
            )
            return []

    class Django:
        model = Note

    class Meta:
        parallel_indexing = True
        queryset_pagination = 50
