# -*- coding: utf-8 -*-

from simpleapi.message.common import json

__all__ = ('wrappers', 'Wrapper', 'DefaultWrapper')

class WrappersSingleton(object):
    """This singleton takes care of all registered wrappers. You can easily 
    register your own wrapper for use in both the Namespace and python client.
    """

    _wrappers = {}

    def __new__(cls):
        it = cls.__dict__.get("__it__")
        if it is not None:
            return it
        cls.__it__ = it = object.__new__(cls)
        return it

    def register(self, name, wrapper, override=False):
        """
            Register the given wrapper
        """
        if not isinstance(wrapper(None, ), Wrapper):
            raise TypeError(u"You can only register a Wrapper not a %s" % wrapper)

        if name in self._wrappers and not override:
            raise AttributeError(u"%s is already a valid wrapper type, try a new name" % name)

        self._wrappers[name] = wrapper

    def copy(self):
        return dict(**self._wrappers)

    def __contains__(self, value):
        return value in self._wrappers

    def __getitem__(self, name):
        return self._wrappers.get(name)

    def __setitem__(self, *args):
        raise AttributeError

wrappers = WrappersSingleton()

class Wrapper(object):
    """The baseclass wrapper you can use as a basis for your own wrapper"""

    def __init__(self, sapi_request):
        self.sapi_request = sapi_request
        self.session = getattr(sapi_request, 'session', None)

    def _build(self, errors, result):
        if isinstance(errors, basestring):
            errors = [errors,]

        if errors:
            assert isinstance(errors, (list, tuple))

        return self.build(errors=errors, result=result)

    def _parse(self, items):
        return self.parse(items=items)

    def parse(self, items):
        raise NotImplementedError

    def build(self, errors, result):
        raise NotImplementedError

class DefaultWrapper(Wrapper):
    def parse(self, items):
        return items

    def build(self, errors, result):
        r = {}
        if errors:
            r['success'] = False
        else:
            r['success'] = True
        if errors:
            r['errors'] = errors
        if result is not None:
            r['result'] = result
        return r

class ExtJSWrapper(Wrapper):
    @staticmethod
    def build_errors(errors):
        assert isinstance(errors, (basestring, tuple, list))
        
        if isinstance(errors, basestring) or \
            (isinstance(errors, (tuple, list)) and \
            len(errors) == 1):
            return {
                'msg': isinstance(errors, (tuple, list)) and errors[0] or errors
            }
        elif isinstance(errors, (tuple, list)) and \
            len(errors) > 0:
            errmsg, errors = errors[0], errors[1]
            assert isinstance(errmsg, basestring)
            assert isinstance(errors, dict)
            
            return {
                'msg': errmsg,
                'errors': errors,
            }

    def parse(self, items):
        return items

    def build(self, errors, result):
        r = {}
        if errors:
            r['success'] = False
        else:
            r['success'] = True
        if errors:
            r.update(self.build_errors(errors))

        if result is not None:
            for key, value in self.build_result(result):
                r[key] = value

        return r

class ExtJSFormWrapper(ExtJSWrapper):
    def build_result(self, result):
        yield ('data', result)

class ExtJSStoreWrapper(ExtJSWrapper):
    def build_result(self, result):
        yield ('rows', result)
        yield ('results', len(result))

class ExtJSDirectWrapper(Wrapper):
    def build(self, errors, result):
        if getattr(self.session._internal, 'formHandler', False):
            r = {
                'type': self.session._internal.type,
                'tid': self.session._internal.tid,
                'action': self.session._internal.action,
                'method': self.session._internal.method,
                'result': {}
            }
            
            if errors:
                r['result'].update(ExtJSWrapper.build_errors(errors))
                r['result']['success'] = False
            else:
                r['result']['success'] = True
                r['result']['data'] = result
            
            return r
        else:
            if errors:
                return {
                    'type': 'exception',
                    'message': ". ".join(errors),
                    'where': 'n/a'
                }
            else:
                return {
                    'result': result,
                    'type': self.session._internal.type,
                    'tid': self.session._internal.tid,
                    'action': self.session._internal.action,
                    'method': self.session._internal.method
                }

    def parse(self, items):
        if items.has_key('extUpload'):
            # {u'username': u'a', u'extAction': u'users', u'extUpload': u'false', u'uid': u'123', u'extMethod': u'login', u'extTID': u'4', u'password': u'b', u'extType': u'rpc'}

            # formHandler true
            d = {
                '_call': items.pop('extMethod', ''),
            }

            self.session._internal.formHandler = True
            self.session._internal.type = items.pop('extType', '')
            self.session._internal.tid = items.pop('extTID', '')
            self.session._internal.action = items.pop('extAction', '') # class
            self.session._internal.method = d['_call']# method

            d.update(items)
            return d
        else:
            # formHandle false
            data = items.keys()[0]
            data = json.loads(data)
            d = {
                '_call': data.pop('method', ''),
            }

            if data.get('data') and len(data['data']) > 0 and \
                not isinstance(data['data'][0], dict):
                raise ValueError(u'data must be a hashable/an array of key/value arguments')

            self.session._internal.formHandler = False
            self.session._internal.type = data.pop('type', '')
            self.session._internal.tid = data.pop('tid', '')
            self.session._internal.action = data.pop('action', '') # class
            self.session._internal.method = d['_call']# method

            data = data.get('data')
            if data:
                data = data[0]
            else:
                data = {}
            d.update(data)
            return d

wrappers.register('default', DefaultWrapper)
wrappers.register('extjsform', ExtJSFormWrapper)
wrappers.register('extjsstore', ExtJSStoreWrapper)
wrappers.register('extjsdirect', ExtJSDirectWrapper)