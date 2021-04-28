from django.conf import settings
from django.contrib import admin
from django.urls import include, path
from drf_yasg import openapi
from drf_yasg.views import get_schema_view
from rest_framework import permissions
from rest_framework_extensions.routers import ExtendedSimpleRouter

from miqa.core.rest import (
    ExperimentViewSet,
    ImageViewSet,
    ScanViewSet,
    SessionViewSet,
    SiteViewSet,
)

router = ExtendedSimpleRouter(trailing_slash=False)
session_router = router.register('sessions', SessionViewSet, basename='session')
session_router.register(
    'experiments',
    ExperimentViewSet,
    basename='experiment',
    parents_query_lookups=['session__id'],
).register(
    'scans',
    ScanViewSet,
    basename='scan',
    parents_query_lookups=['experiment__session__id', 'experiment__id'],
).register(
    'images',
    ImageViewSet,
    basename='image',
    parents_query_lookups=['scan__experiment__session__id', 'scan__experiment__id', 'scan__id'],
)
session_router.register(
    'sites',
    SiteViewSet,
    basename='site',
    parents_query_lookups=['session__id'],
)

# OpenAPI generation
schema_view = get_schema_view(
    openapi.Info(title='MIQA', default_version='v1', description=''),
    public=True,
    permission_classes=(permissions.AllowAny,),
)

urlpatterns = [
    path('accounts/', include('allauth.urls')),
    path('oauth/', include('oauth2_provider.urls', namespace='oauth2_provider')),
    path('admin/', admin.site.urls),
    path('api/v1/', include(router.urls)),
    path('api/docs/redoc/', schema_view.with_ui('redoc'), name='docs-redoc'),
    path('api/docs/swagger/', schema_view.with_ui('swagger'), name='docs-swagger'),
]

if settings.DEBUG:
    import debug_toolbar

    urlpatterns = [path('__debug__/', include(debug_toolbar.urls))] + urlpatterns
