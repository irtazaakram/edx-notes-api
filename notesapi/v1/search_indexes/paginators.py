"""
Paginator for Document Notes where storage is Elasticsearch or Database.
"""

from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response

from ..utils import NotesPaginatorMixin

__all__ = ('NotesPagination',)


class NotesPagination(NotesPaginatorMixin, PageNumberPagination):
    """
    Custom pagination class for Student Document Notes.
    """

    page_size = 25  # Default page size, can be overridden

    def get_paginated_response(self, data):
        """
        Return paginated response structure.
        """
        return Response({
            'count': self.page.paginator.count,
            'next': self.get_next_link(),
            'previous': self.get_previous_link(),
            'current': self.page.number,
            'num_pages': self.page.paginator.num_pages,
            'results': data
        })
