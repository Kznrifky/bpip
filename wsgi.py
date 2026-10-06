"""WSGI transport adapter. Business routes remain shared with the local server."""
import io
from email.message import Message
from http import HTTPStatus

from server import Handler


class WSGIHandler(Handler):
    def __init__(self, environ):
        self.command = environ['REQUEST_METHOD']
        self.path = environ.get('PATH_INFO', '/')
        if environ.get('QUERY_STRING'):
            self.path += '?' + environ['QUERY_STRING']
        self.client_address = (environ.get('REMOTE_ADDR', ''), 0)
        self.headers = Message()
        for key, value in environ.items():
            if key.startswith('HTTP_'):
                self.headers[key[5:].replace('_', '-')] = value
        for key in ('CONTENT_TYPE', 'CONTENT_LENGTH'):
            if environ.get(key):
                self.headers[key.replace('_', '-')] = environ[key]
        self.rfile = environ['wsgi.input']
        self.wfile = io.BytesIO()
        self.response_status = 200
        self.response_headers = []

    def send_response(self, code, message=None):
        self.response_status = code
        self.response_headers = []

    def send_header(self, key, value):
        self.response_headers.append((key, str(value)))

    def end_headers(self):
        pass


def application(environ, start_response):
    handler = WSGIHandler(environ)
    if handler.command in ('GET', 'HEAD'):
        handler.do_GET()
    elif handler.command == 'POST':
        handler.do_POST()
    else:
        handler.respond({'error': 'Metode tidak diizinkan.'}, 405)
        handler.send_header('Allow', 'GET, HEAD, POST')
    start_response(f'{handler.response_status} {HTTPStatus(handler.response_status).phrase}', handler.response_headers)
    return [b'' if handler.command == 'HEAD' else handler.wfile.getvalue()]
