'''
CRUD resource models.
'''

from abc import ABCMeta, abstractmethod
import json

from werkzeug.wrappers import Response
from werkzeug.exceptions import NotFound, Conflict, BadRequest, Gone


class CRUDResource(metaclass=ABCMeta):

    '''An abstract class defining the interface of CRUD resources.'''

    @abstractmethod
    def create():
        pass

    @abstractmethod
    def read():
        pass

    @abstractmethod
    def update():
        pass

    @abstractmethod
    def delete():
        pass


class InMemoryResource(CRUDResource):

    '''A "in-memory" backend for CRUD resources.'''

    def __init__(self, location):
        self.items = {}
        self._uid = -1
        self.location = '/{}'.format(location)

    def _flatten(self, resources, item_id):
        flat = self.items[item_id].copy()
        flat['id'] = item_id
        return flat

    def _read_payload(self, resources, request):
        '''A helper function to read the payload from the request's body.'''
        payload = json.loads(request.data.decode())
        if self.validate_payload(resources, payload):
            return payload
        raise BadRequest

    def _create_payload(self, resources, uid=None):
        '''A helper function to create the response's payload.'''
        if uid is None:
            payload = [self._flatten(resources, uid) for uid in self.items]
        else:
            payload = self._flatten(resources, uid)
        return json.dumps(payload, indent=4)

    def validate_payload(self, resources, payload):
        return True

    def validate_uid(self, uid):
        if uid in self.items:
            return True
        if 0 <= uid <= self._uid:
            raise Gone
        raise NotFound

    def create(self, resources, request):
        payload = self._read_payload(resources, request)
        self._uid += 1
        self.items[self._uid] = payload
        location = '{}/{}'.format(self.location, self._uid)
        return Response(json.dumps(self._flatten(resources, self._uid)),
                        headers=[('Location', location)],
                        status=201)

    def read(self, resources, request, uid=None):
        if uid is not None:
            self.validate_uid(uid)
        payload = self._create_payload(resources, uid)
        return Response(payload, mimetype='application/json', status=200)

    def update(self, resources, request, uid):
        self.validate_uid(uid)
        payload = self._read_payload(resources, request)
        if payload.get('id') != uid:
            raise BadRequest  # Additional validation (consistency check)
        self.items[uid] = payload
        return Response(status=204)

    def delete(self, resources, request, uid):
        self.validate_uid(uid)
        del self.items[uid]
        return Response(status=204)


class Tasks(InMemoryResource):

    def validate_payload(self, resources, payload):
        if not isinstance(payload, dict):
            return False
        if not isinstance(payload.get('done'), bool):  # Task completed?
            return False
        if not isinstance(payload.get('description'), str):  # Task description
            return False
        if len(payload) != (3 if 'id' in payload else 2):  # No extra data
            return False
        return True

    def delete(self, resources, request, uid):
        # A task can only be deleted if no list uses it
        if any(uid in _list['tasks']
               for _list in resources['lists'].items.values()):
            raise Conflict
        return super().delete(resources, request, uid)


class Lists(InMemoryResource):

    def _flatten(self, resources, item_id):
        '''Beside flattening, it expands the referenced tasks.'''
        flat = self.items[item_id].copy()
        flat['id'] = item_id
        flat['tasks'] = [resources['tasks']._flatten(resources, tid)
                         for tid in flat['tasks']]
        return flat

    def validate_payload(self, resources, payload):
        if not isinstance(payload, dict):
            return False
        if not isinstance(payload.get('description'), str):  # List title
            return False
        if not isinstance(payload.get('tasks'), list):  # List of task uids
            return False
        # A list cannot contain duplicate tasks
        if len(payload['tasks']) != len(set(payload['tasks'])):
            return False
        # A list can only contain existing tasks...
        if not all([uid in resources['tasks'].items.keys()
                    for uid in payload['tasks']]):
            return False
        return True
