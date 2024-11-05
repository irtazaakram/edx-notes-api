from django.urls import path

from notesapi.v1.views import (
    AnnotationDetailView,
    AnnotationListView,
    AnnotationRetireView,
    AnnotationSearchView,
)

app_name = "notesapi.v1"

urlpatterns = [
    path("annotations/", AnnotationListView.as_view(), name="annotations"),
    path("retire_annotations/", AnnotationRetireView.as_view(), name="annotations_retire"),
    path(
        "annotations/<str:annotation_id>/",
        AnnotationDetailView.as_view(),
        name="annotations_detail",
    ),
    path("search/", AnnotationSearchView.as_view(), name="annotations_search"),
]
