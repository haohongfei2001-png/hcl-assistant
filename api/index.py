"""Vercel Python handler. No credentials, database work or jobs at module import."""
from http.server import BaseHTTPRequestHandler
from apps.api.server import handler as request_handler
from apps.api.cloud_server import application

class handler(BaseHTTPRequestHandler):
    def __init__(self,*args,**kwargs):
        app=application()
        try: request_handler(app)(*args,**kwargs)
        finally: app.close()
