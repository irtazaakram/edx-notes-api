from itertools import chain

from django.db.models import Q

from notesapi.v1.utils import Request

__all__ = ('CompoundSearchFilterBackend', 'FilteringFilterBackend')


class CompoundSearchFilterBackend:
    """
    Custom compound search backend to search on specified fields.
    """

    search_fields = ('text', 'tags')

    def get_search_query_params(self, request):
        """
        Get search query params by extracting values for each search field.

        :param request: Django REST framework request.
        :type request: rest_framework.request.Request
        :return: List of search query params.
        :rtype: list
        """
        query_params = request.query_params.copy()
        return list(
            chain.from_iterable(
                query_params.getlist(search_param, [])
                for search_param in self.search_fields
            )
        )

    def filter_queryset(self, request, queryset, view):  # pylint: disable=unused-argument
        """
        Apply filtering based on the search fields to the queryset.
        """
        search_terms = self.get_search_query_params(request)
        for term in search_terms:
            queryset = queryset.filter(Q(text__icontains=term) | Q(tags__icontains=term))
        return queryset


class FilteringFilterBackend:
    """
    Custom filtering backend to simulate behavior of previous filtering backend.
    """

    def get_filter_query_params(self, request, view):
        """
        Retrieve query parameters to filter on, using a simulated request.
        """
        simulated_request = Request(view.query_params)
        return simulated_request.query_params

    def filter_queryset(self, request, queryset, view):
        """
        Filter queryset based on the view's query parameters.
        """
        filter_params = self.get_filter_query_params(request, view)
        for param, value in filter_params.items():
            filter_criteria = {param: value}
            queryset = queryset.filter(**filter_criteria)
        return queryset
