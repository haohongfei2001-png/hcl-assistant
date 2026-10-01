"""Vercel HTTP handler; app creation and cleanup belong to each request."""
from apps.api.server import handler as _request_handler
from apps.api.cloud_server import application as _create_application

# Do not export the internal factory as `app` or `application`: Vercel would
# discover it before `handler` and incorrectly treat it as an ASGI/WSGI app.
class handler(_request_handler(None)):
    def _dispatch(self, method):
        self.application=_create_application()
        try:
            method()
        finally:
            self.application.close()
            self.application=None

    def do_GET(self):
        self._dispatch(super().do_GET)

    def do_POST(self):
        self._dispatch(super().do_POST)
