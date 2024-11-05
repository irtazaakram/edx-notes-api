import datetime
import traceback

from django.conf import settings
from django.db import connection
from django.http import HttpResponse, JsonResponse
from elasticsearch.exceptions import TransportError
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

try:
    import newrelic.agent
except ImportError:
    newrelic = None

if not settings.ES_DISABLED:
    from elasticsearch_dsl.connections import connections

    def get_es_connection():
        return connections.get_connection()

@api_view(['GET'])
@permission_classes([AllowAny])
def root(request):
    """
    Root view.
    """
    return Response({"name": "edX Notes API", "version": "1"})

@api_view(['GET'])
@permission_classes([AllowAny])
def robots(request):
    """
    robots.txt
    """
    return HttpResponse("User-agent: * Disallow: /", content_type="text/plain")

@api_view(['GET'])
@permission_classes([AllowAny])
def heartbeat(request):
    """
    ElasticSearch and database are reachable and ready to handle requests.
    """
    if newrelic:  # pragma: no cover
        newrelic.agent.ignore_transaction()

    try:
        db_status()
    except Exception:
        return JsonResponse({"OK": False, "check": "db"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    if not settings.ES_DISABLED and not get_es_connection().ping():
        return JsonResponse({"OK": False, "check": "es"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    return JsonResponse({"OK": True}, status=status.HTTP_200_OK)

@api_view(['GET'])
@permission_classes([AllowAny])
def selftest(request):
    """
    Manual test endpoint.
    """
    start_time = datetime.datetime.now()
    es_status = None

    if not settings.ES_DISABLED:
        try:
            es_status = get_es_connection().info()
        except TransportError:
            return Response(
                {"es_error": traceback.format_exc()},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    try:
        db_status()
        db_status_msg = "OK"
    except Exception:
        return Response(
            {"db_error": traceback.format_exc()},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

    time_elapsed_ms = int((datetime.datetime.now() - start_time).total_seconds() * 1000)

    response = {
        "db": db_status_msg,
        "time_elapsed": time_elapsed_ms,
        **({"es": es_status} if es_status else {})
    }

    return Response(response)

def db_status():
    """
    Return database status.
    """
    with connection.cursor() as cursor:
        cursor.execute("SELECT 1")
        return cursor.fetchone()
