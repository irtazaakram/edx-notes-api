from django.urls import include, path, re_path
from drf_spectacular.views import SpectacularAPIView, SpectacularRedocView, SpectacularSwaggerView
from notesserver import views as notesserver_views

urlpatterns = [
    path('heartbeat/', notesserver_views.heartbeat, name='heartbeat'),
    path('selftest/', notesserver_views.selftest, name='selftest'),
    re_path(r'^robots.txt$', notesserver_views.robots, name='robots'),
    path('', notesserver_views.root, name='root'),
    path('api/', include('notesapi.urls', namespace='api')),
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/schema/swagger-ui/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
    path('api/schema/redoc/', SpectacularRedocView.as_view(url_name='schema'), name='redoc'),
]
