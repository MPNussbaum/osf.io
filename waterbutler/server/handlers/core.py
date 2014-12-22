import asyncio

import tornado.web

from stevedore import driver

from waterbutler.server import settings
from waterbutler.server import exceptions
from waterbutler.server.identity import get_identity


CORS_ACCEPT_HEADERS = [
    'Content-Type',
    'Cache-Control',
    'X-Requested-With',
]


def list_or_value(value):
    assert isinstance(value, list)
    if len(value) == 0:
        return None
    if len(value) == 1:
        # Remove leading slashes as they break things
        return value[0].decode('utf-8').lstrip('/')
    return [item.decode('utf-8') for item in value]


class BaseHandler(tornado.web.RequestHandler):

    ACTION_MAP = {}

    def set_default_headers(self):
        self.set_header('Access-Control-Allow-Origin', '*')

    @asyncio.coroutine
    def prepare(self):
        self.arguments = {
            key: list_or_value(value)
            for key, value in self.request.query_arguments.items()
        }

        try:
            self.arguments['action'] = self.ACTION_MAP[self.request.method]
        except KeyError:
            return

        self.payload = yield from get_identity(settings.IDENTITY_METHOD, **self.arguments)

        self.manager = driver.DriverManager(
            namespace='waterbutler.providers',
            name=self.arguments['provider'],
            invoke_on_load=True,
            invoke_args=(
                self.payload['auth'],
                self.payload['credentials'],
                self.payload['settings'],
            ),
        )
        self.provider = self.manager.driver

    def write_error(self, status_code, exc_info):
        etype, exc, _ = exc_info
        if etype is exceptions.WaterButlerError:
            if exc.data:
                self.finish(exc.data)
                return

        self.finish({
            "code": status_code,
            "message": self._reason,
        })

    def options(self):
        self.set_status(204)
        self.set_header('Access-Control-Allow-Methods', 'PUT, DELETE'),
        self.set_header('Access-Control-Allow-Headers', ', '.join(CORS_ACCEPT_HEADERS))