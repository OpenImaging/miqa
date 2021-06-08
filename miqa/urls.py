from django.conf import settings
from django.contrib import admin
from django.urls import include, path
from drf_yasg import openapi
from drf_yasg.views import get_schema_view
from rest_framework import permissions, routers

from miqa.core.rest import (
    AnnotationViewSet,
    ExperimentViewSet,
    ImageViewSet,
    ScanNoteViewSet,
    ScanViewSet,
    SessionViewSet,
    SiteViewSet,
    UserViewSet,
)

router = routers.SimpleRouter(trailing_slash=False)
router.register('sessions', SessionViewSet, basename='session')
router.register('experiments', ExperimentViewSet)
router.register('scans', ScanViewSet)
router.register('images', ImageViewSet)
router.register('sites', SiteViewSet)
router.register('scan_notes', ScanNoteViewSet)
router.register('users', UserViewSet)
router.register('annotations', AnnotationViewSet)

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
