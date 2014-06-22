#!/usr/bin/env python3
'''
Toy ToDo WSGI Application relying on werkzeug.
'''

import os

from werkzeug.wrappers import Request
from werkzeug.routing import Map, Rule
from werkzeug.exceptions import HTTPException, NotFound
from werkzeug.wsgi import SharedDataMiddleware

from resources import Tasks, Lists

HTTP_TO_CRUD = {
    'POST': 'create',
    'GET': 'read',
    'PUT': 'update',
    'DELETE': 'delete',
}


class Application(object):

    def __init__(self):
        self.url_map = Map([
            # Tasks
            Rule('/tasks', methods=['GET', 'POST'], endpoint='tasks'),
            Rule('/tasks/<int:uid>', methods=['GET', 'PUT', 'DELETE'],
                 endpoint='tasks'),
            # Lists
            Rule('/lists', methods=['GET', 'POST'], endpoint='lists'),
            Rule('/lists/<int:uid>', methods=['GET', 'PUT', 'DELETE'],
                 endpoint='lists'),
        ])
        self.resources = {
            'lists': Lists('lists'),
            'tasks': Tasks('tasks'),
        }

    def dispatch_request(self, request):
        adapter = self.url_map.bind_to_environ(request.environ)
        try:
            endpoint, values = adapter.match()
            resource = self.resources[endpoint]
            handler = getattr(resource, HTTP_TO_CRUD[request.method])
            return handler(self.resources, request, **values)
        except (HTTPException, NotFound) as e:
            return e

    def wsgi_app(self, environ, start_response):
        request = Request(environ)
        response = self.dispatch_request(request)
        return response(environ, start_response)

    def __call__(self, environ, start_response):
        return self.wsgi_app(environ, start_response)


if __name__ == '__main__':
    from werkzeug.serving import run_simple
    app = Application()
    app.wsgi_app = SharedDataMiddleware(app.wsgi_app, {
        '/static': os.path.join(os.path.dirname(__file__), 'static')
    })
    run_simple('127.0.0.1', 5000, app, use_debugger=True, use_reloader=True)
