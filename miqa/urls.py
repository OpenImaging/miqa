from django.conf import settings
from django.contrib import admin
from django.urls import include, path
from drf_yasg import openapi
from drf_yasg.views import get_schema_view
from rest_framework import permissions, routers

from miqa.core.rest import (
    EmailView,
    ExperimentViewSet,
    FrameViewSet,
    HomePageView,
    AccountInactiveView,
    LogoutView,
    ProjectViewSet,
    ScanDecisionViewSet,
    ScanViewSet,
    UserViewSet,
)

router = routers.SimpleRouter(trailing_slash=False)
router.register('projects', ProjectViewSet, basename='project')
router.register('experiments', ExperimentViewSet, basename='experiment')
router.register('scans', ScanViewSet, basename='scan')
router.register('frames', FrameViewSet, basename='frame')
router.register('scan-decisions', ScanDecisionViewSet, basename='scan_decisions')
router.register('users', UserViewSet)

# OpenAPI generation
schema_view = get_schema_view(
    openapi.Info(title='MIQA', default_version='v1', description=''),
    public=True,
    permission_classes=(permissions.IsAuthenticated,),
)

urlpatterns = [
    path('', HomePageView, name='home'),
    path('accounts/inactive/', AccountInactiveView.as_view()),
    path('accounts/', include('allauth.urls')),
    path('oauth/', include('oauth2_provider.urls', namespace='oauth2_provider')),
    path('admin/', admin.site.urls),
    path('api/v1/', include(router.urls)),
    path('api/v1/email', EmailView.as_view()),
    path('api/v1/logout/', LogoutView.as_view()),
    path('api/docs/redoc/', schema_view.with_ui('redoc'), name='docs-redoc'),
    path('api/docs/swagger/', schema_view.with_ui('swagger'), name='docs-swagger'),
]

if settings.DEBUG:
    import debug_toolbar

    urlpatterns = [path('__debug__/', include(debug_toolbar.urls))] + urlpatterns
