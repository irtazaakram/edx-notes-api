import json
import logging

import newrelic.agent
from django.conf import settings
from django.core.exceptions import ValidationError
from django.db.models import Q
from django.urls import reverse
from django.utils.translation import gettext as _
from rest_framework import status
from rest_framework.generics import GenericAPIView, ListAPIView
from rest_framework.response import Response
from rest_framework.views import APIView

from notesapi.v1.models import Note
from notesapi.v1.search_indexes.documents import NoteDocument
from notesapi.v1.serializers import NoteSerializer

if not settings.ES_DISABLED:
    from django_elasticsearch_dsl_drf.constants import (
        LOOKUP_FILTER_TERM,
        LOOKUP_QUERY_IN,
        SEPARATOR_LOOKUP_COMPLEX_VALUE,
    )
    from django_elasticsearch_dsl_drf.filter_backends import (
        DefaultOrderingFilterBackend,
        HighlightBackend,
    )
    from elasticsearch_dsl import Search
    from elasticsearch_dsl.connections import connections

    from notesapi.v1.search_indexes.backends import (
        CompoundSearchFilterBackend,
        FilteringFilterBackend,
    )
    from notesapi.v1.search_indexes.paginators import NotesPagination as ESNotesPagination
    from notesapi.v1.search_indexes.serializers import (
        NoteDocumentSerializer as NotesElasticSearchSerializer,
    )

log = logging.getLogger(__name__)


class AnnotationsLimitReachedError(Exception):
    """
    Exception when trying to create more than allowed annotations
    """


class AnnotationSearchView(ListAPIView):
    """
    **Use Case**

        * Search and return a list of annotations for a user.

            The annotations are always sorted in descending order by updated date.

            Response is paginated by default except usage_id based search.

            Each page in the list contains 25 annotations by default. The page
            size can be altered by passing parameter "page_size=<page_size>".

            Http400 is returned if the format of the request is not correct.

    **Search Types**

        * There are two types of searches one can perform

            * Database

                If ElasticSearch is disabled or text query param is not present.

            * ElasticSearch

    **Example Requests**

        GET /api/v1/search/
        GET /api/v1/search/?course_id={course_id}&user={user_id}
        GET /api/v1/search/?course_id={course_id}&user={user_id}&usage_id={usage_id}
        GET /api/v1/search/?course_id={course_id}&user={user_id}&usage_id={usage_id}&usage_id={usage_id} ...

    **Query Parameters for GET**

        All the parameters are optional.

        * course_id: Id of the course.

        * user: Anonymized user id.

        * usage_id: The identifier string of the annotations XBlock.

        * text: Student's thoughts on the quote

        * highlight: dict. Only used when search from ElasticSearch. It contains two keys:

            * highlight_tag: String. HTML tag to be used for highlighting the text. Default is "em"

            * highlight_class: String. CSS class to be used for highlighting the text.

    **Response Values for GET**

        * count: The number of annotations in a course.

        * next: The URI to the next page of annotations.

        * previous: The URI to the previous page of annotations.

        * current: Current page number.

        * num_pages: The number of pages listing annotations.

        * results: A list of annotations returned. Each collection in the list contains these fields.

            * id: String. The primary key of the note.

            * user: String. Anonymized id of the user.

            * course_id: String. The identifier string of the annotations course.

            * usage_id: String. The identifier string of the annotations XBlock.

            * quote: String. Quoted text.

            * text: String. Student's thoughts on the quote.

            * ranges: List. Describes position of quote.

            * tags: List. Comma separated tags.

            * created: DateTime. Creation datetime of annotation.

            * updated: DateTime. When was the last time annotation was updated.
    """

    document = NoteDocument
    search_fields = ("text", "tags")
    filter_fields = {
        "course_id": "course_id",
        "user": "user",
        "usage_id": {"field": "usage_id", "lookups": [LOOKUP_QUERY_IN, LOOKUP_FILTER_TERM]},
    }
    highlight_fields = {
        "text": {
            "enabled": True,
            "options": {"pre_tags": ["<em>"], "post_tags": ["</em>"], "number_of_fragments": 0},
        },
        "tags": {
            "enabled": True,
            "options": {"pre_tags": ["<em>"], "post_tags": ["</em>"], "number_of_fragments": 0},
        },
    }
    ordering = ("-updated",)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.initiate_es_state() if not settings.ES_DISABLED else None

    def initiate_es_state(self):
        """
        Initiates elasticsearch specific state if elasticsearch is enabled.

        Should be called in the class `__init__` method.
        """
        self.client = connections.get_connection(self.document._get_using())
        self.index = self.document._index._name
        self.search = Search(using=self.client, index=self.index)

    @property
    def is_es_disabled(self):
        """
        Predicate instance method.

        Search in DB when ES is not available or there is no need to bother it
        """
        return settings.ES_DISABLED or "text" not in self.request.query_params

    def get_queryset(self):
        queryset = Note.objects.filter(**self.query_params).order_by("-updated")
        if self.is_es_disabled:
            text_param = self.request.query_params.get("text")
            if text_param:
                queryset = queryset.filter(
                    Q(text__icontains=text_param) | Q(tags__icontains=text_param)
                )
        else:
            queryset = self.search.query()
            queryset.model = self.document.Django.model
        return queryset

    def get_serializer_class(self):
        """
        Return the class to use for the serializer.

        Defaults to using `NoteSerializer` if elasticsearch is disabled
        or `NotesElasticSearchSerializer` if elasticsearch is enabled
        """
        return NoteSerializer if self.is_es_disabled else NotesElasticSearchSerializer

    @property
    def paginator(self):
        """
        The paginator instance associated with the view and used data source, or `None`.
        """
        if not hasattr(self, "_paginator"):
            self._paginator = (
                (self.pagination_class() if self.is_es_disabled else ESNotesPagination())
                if self.pagination_class
                else None
            )
        return self._paginator

    def filter_queryset(self, queryset):
        """
        Given a queryset, filter it with whichever filter backend is in use.

        Do not filter additionally if mysql db used or use `CompoundSearchFilterBackend`
        and `HighlightBackend` if elasticsearch is the data source.
        """
        if self.is_es_disabled:
            return queryset
        filter_backends = [
            FilteringFilterBackend,
            CompoundSearchFilterBackend,
            DefaultOrderingFilterBackend,
            HighlightBackend if self.request.query_params.get("highlight") else None,
        ]
        for backend in filter_backends:
            queryset = backend().filter_queryset(self.request, queryset, view=self)
        return queryset

    def build_query_params_state(self):
        """
        Builds a custom query params.

        Use them in order to search annotations in most appropriate storage.
        """
        self.query_params = {}
        params = self.request.query_params.dict()
        usage_ids = self.request.query_params.getlist("usage_id")
        self.query_params["usage_id__in"] = (
            SEPARATOR_LOOKUP_COMPLEX_VALUE.join(usage_ids)
            if usage_ids and not self.is_es_disabled
            else usage_ids
        )
        if "course_id" in params:
            self.query_params["course_id"] = params["course_id"]
        if "user" in params:
            self.query_params["user" if not self.is_es_disabled else "user_id"] = params["user"]

    def get(self, request, *args, **kwargs):
        """Search annotations in most appropriate storage."""
        self.build_query_params_state()
        return super().get(request, *args, **kwargs)


class AnnotationRetireView(GenericAPIView):
    """
    Administrative functions for the notes service.
    """

    def post(self, request):
        """
        Delete all annotations for a user.
        """
        user_id = request.data.get("user")
        if not user_id:
            return Response(status=status.HTTP_400_BAD_REQUEST)
        Note.objects.filter(user_id=user_id).delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class AnnotationListView(GenericAPIView):
    """
    **Use Case**

        * Get a paginated list of annotations for a user.

            The annotations are always sorted in descending order by updated date.

            Each page in the list contains 25 annotations by default. The page
            size can be altered by passing parameter "page_size=<page_size>".

            HTTP 400 Bad Request: The format of the request is not correct.

        * Create a new annotation for a user.

            HTTP 400 Bad Request: The format of the request is not correct, or the maximum number of notes for a
            user has been reached.

            HTTP 201 Created: Success.

        * Delete all annotations for a user.

            HTTP 400 Bad Request: The format of the request is not correct.

            HTTP 200 OK: Either annotations from the user were deleted, or no annotations for the user were found.

    **Example Requests**

        GET /api/v1/annotations/?course_id={course_id}&user={user_id}

        POST /api/v1/annotations/
        user={user_id}&course_id={course_id}&usage_id={usage_id}&ranges={ranges}&quote={quote}

        DELETE /api/v1/annotations/
        user={user_id}

    **Query Parameters for GET**

        Both the course_id and user must be provided.

        * course_id: Id of the course.

        * user: Anonymized user id.

    **Response Values for GET**

        * count: The number of annotations in a course.

        * next: The URI to the next page of annotations.

        * previous: The URI to the previous page of annotations.

        * current: Current page number.

        * num_pages: The number of pages listing annotations.

        * results:  A list of annotations returned. Each collection in the list contains these fields.

            * id: String. The primary key of the note.

            * user: String. Anonymized id of the user.

            * course_id: String. The identifier string of the annotations course.

            * usage_id: String. The identifier string of the annotations XBlock.

            * quote: String. Quoted text.

            * text: String. Student's thoughts on the quote.

            * ranges: List. Describes position of quote.

            * tags: List. Comma separated tags.

            * created: DateTime. Creation datetime of annotation.

            * updated: DateTime. When was the last time annotation was updated.

    **Form-encoded data for POST**

        user, course_id, usage_id, ranges and quote fields must be provided.

    **Response Values for POST**

        * id: String. The primary key of the note.

        * user: String. Anonymized id of the user.

        * course_id: String. The identifier string of the annotations course.

        * usage_id: String. The identifier string of the annotations XBlock.

        * quote: String. Quoted text.

        * text: String. Student's thoughts on the quote.

        * ranges: List. Describes position of quote in the source text.

        * tags: List. Comma separated tags.

        * created: DateTime. Creation datetime of annotation.

        * updated: DateTime. When was the last time annotation was updated.

    **Form-encoded data for DELETE**

        * user: Anonymized user id.

    **Response Values for DELETE**

        * no content.

    """

    serializer_class = NoteSerializer

    def get(self, request):
        """
        Get paginated list of all annotations.
        """
        params = request.query_params.dict()
        if not {"course_id", "user"}.issubset(params):
            return Response(status=status.HTTP_400_BAD_REQUEST)
        notes = Note.objects.filter(course_id=params["course_id"], user_id=params["user"]).order_by(
            "-updated"
        )
        page = self.paginate_queryset(notes)
        return self.get_paginated_response(self.get_serializer(page, many=True).data)

    def post(self, request):
        data = request.data
        """
        Create a new annotation.

        Returns 400 request if bad payload is sent or it was empty object.
        """
        if not data or "id" in data:
            return Response(status=status.HTTP_400_BAD_REQUEST)

        try:
            total_notes = Note.objects.filter(
                user_id=data["user"], course_id=data["course_id"]
            ).count()
            if total_notes >= settings.MAX_NOTES_PER_COURSE:
                raise AnnotationsLimitReachedError

            note = Note.create(data)
            note.full_clean()

            # Gather metrics for New Relic so we can slice data in New Relic Insights
            newrelic.agent.add_custom_parameter("notes.count", total_notes)
        except ValidationError as e:
            log.debug(e, exc_info=True)
            return Response(status=status.HTTP_400_BAD_REQUEST)
        except AnnotationsLimitReachedError:
            error_message = _(
                "You can create up to {max_num} notes. You must remove some notes before you can add new ones."
            ).format(max_num=settings.MAX_NOTES_PER_COURSE)
            log.info(f"Exceeded max annotations: {settings.MAX_NOTES_PER_COURSE}")
            return Response({"error_msg": error_message}, status=status.HTTP_400_BAD_REQUEST)

        note.save()
        serializer = NoteSerializer(note)
        location = reverse("api:v1:annotations_detail", kwargs={"annotation_id": note.id})
        return Response(
            serializer.data, status=status.HTTP_201_CREATED, headers={"Location": location}
        )


class AnnotationDetailView(APIView):
    """
    **Use Case**

        * Get a single annotation.

        * Update an annotation.

        * Delete an annotation.

    **Example Requests**

        GET /api/v1/annotations/<annotation_id>
        PUT /api/v1/annotations/<annotation_id>
        DELETE /api/v1/annotations/<annotation_id>

    **Query Parameters for GET**

        HTTP404 is returned if annotation_id is missing.

        * annotation_id: Annotation id

    **Query Parameters for PUT**

        HTTP404 is returned if annotation_id is missing and HTTP400 is returned if text and tags are missing.

        * annotation_id: String. Annotation id

        * text: String. Text to be updated

        * tags: List. Tags to be updated

    **Query Parameters for DELETE**

        HTTP404 is returned if annotation_id is missing.

        * annotation_id: Annotation id

    **Response Values for GET**

        * id: String. The primary key of the note.

        * user: String. Anonymized id of the user.

        * course_id: String. The identifier string of the annotations course.

        * usage_id: String. The identifier string of the annotations XBlock.

        * quote: String. Quoted text.

        * text: String. Student's thoughts on the quote.

        * ranges: List. Describes position of quote.

        * tags: List. Comma separated tags.

        * created: DateTime. Creation datetime of annotation.

        * updated: DateTime. When was the last time annotation was updated.

    **Response Values for PUT**

        * same as GET with updated values

    **Response Values for DELETE**

        * HTTP_204_NO_CONTENT is returned
    """

    def get(self, request, annotation_id):
        """
        Get an existing annotation.
        """
        try:
            note = Note.objects.get(id=annotation_id)
        except Note.DoesNotExist:
            return Response("Annotation not found!", status=status.HTTP_404_NOT_FOUND)
        return Response(NoteSerializer(note).data)

    def put(self, request, annotation_id):
        """
        Update an existing annotation.
        """
        try:
            note = Note.objects.get(id=annotation_id)
            note.text = request.data["text"]
            note.tags = json.dumps(request.data["tags"])
            note.full_clean()
            note.save()
            return Response(NoteSerializer(note).data)
        except Note.DoesNotExist:
            return Response("Annotation not found!", status=status.HTTP_404_NOT_FOUND)
        except KeyError as e:
            log.debug(e, exc_info=True)
            return Response(status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, annotation_id):
        """
        Delete an annotation.
        """
        try:
            Note.objects.get(id=annotation_id).delete()
            # Annotation deleted successfully.
            return Response(status=status.HTTP_204_NO_CONTENT)
        except Note.DoesNotExist:
            return Response("Annotation not found!", status=status.HTTP_404_NOT_FOUND)
