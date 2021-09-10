from django.conf import settings
from django.views.generic.base import RedirectView, TemplateView

if settings.HOMEPAGE_REDIRECT_URL:
    # For convenience, we redirect from the API server to the frontend
    # if no URL pattern is specified.

    HomePageView = RedirectView.as_view(url=settings.HOMEPAGE_REDIRECT_URL)

else:
    """
    Serve index.html as a view, to be hosted at /.

    This is used exclusively in production.

    The web client is built and build artifacts are stored in `staticfiles`.
    The whitenoise app hosts all files in `staticfiles` at `/static/`,
    but it would not be good UX
    to access the web client at `http://what.ever/static/index.html`.

    Instead, `staticfiles` is registered as a template directory, so this view can find it.
    This view is then registered with the URL pattern `/`.
    Now the web client will load when visiting `/`, despite technically being hosted at
    `/static/index.html`.
    """
    HomePageView = TemplateView.as_view(template_name='index.html')
