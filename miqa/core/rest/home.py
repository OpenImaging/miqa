from django.views.generic.base import TemplateView


class HomePageView(TemplateView):
    """
    Serve index.html as a view, to be hosted at /.

    This is used exclusively in production.

    The web client is built and build artifacts are stored in `staticfiles`.
    The whitenoise app hosts all files in `staticfiles` at `/static/`, but it would not be good UX
    to access the web client at `http://what.ever/static/index.html`.

    Instead, `staticfiles` is registered as a template directory, so this view can find it.
    This view is then registered with the URL pattern `/`.
    Now the web client will load when visiting `/`, despite technically being hosted at
    `/static/index.html`.
    """

    template_name = 'index.html'
