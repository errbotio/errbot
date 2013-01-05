from inspect import getmembers, ismethod
from json import loads
import logging
from bottle import Bottle, request
from errbot.plugin_manager import get_all_active_plugin_objects


class DynamicBottle(Bottle):
    def del_route(self, route_name):
        deleted_route = None
        for route in self.routes[:]:
            if route.name == route_name:
                self.routes.remove(route)
                deleted_route = route
                break
        if not deleted_route:
            raise ValueError('Cannot find the route %s to delete' % route_name)
        del (self.router.rules[deleted_route.rule])


bottle_app = DynamicBottle()

def try_decode_json(request):
    data = request.body.read().decode()
    try:
        return loads(data)
    except Exception as _:
        return None


def reset_app():
    """Zap everything here, useful for unit tests
    """
    global bottle_app
    bottle_app = DynamicBottle()

class WebView(object):
    def __init__(self, func, form_param):
        self.func = func
        self.form_param = form_param
        self.method_filter = lambda object: ismethod(object) and self.func.__name__ == object.__name__

    def __call__(self, *args, **kwargs):
        name_to_find = self.func.__name__
        logging.debug('All active plugin objects %s ' % get_all_active_plugin_objects())
        for obj in get_all_active_plugin_objects():  # horrible hack to find back the bound method from the unbound function the decorator was able to give us
            matching_members = getmembers(obj, self.method_filter)
            logging.debug('Matching members %s -> %s' % (obj, matching_members))
            if matching_members:
                name, func = matching_members[0]
                if self.form_param:
                    content = request.forms.get(self.form_param)
                    try:
                        content = loads(content)
                    except ValueError:
                        logging.debug('The form parameter is not JSON, return it as a string')
                    response = func(content, **kwargs)
                else:
                    data = try_decode_json(request)
                    if not data:
                        if hasattr(request, 'forms'):
                            data = dict(request.forms)  # form encoded
                        else:
                            data = request.body.read().decode()
                    response = func(data, **kwargs)
                return response if response else ''  # assume None as an OK response (simplifies the client side)

        raise Exception('Problem finding back the correct Handler for func %s' % name_to_find)


def webhook(*args, **kwargs):
    """
        Simple shortcut for the plugins to be notified on webhooks
    """

    def decorate(method, uri_rule, methods=('POST', 'GET'), form_param=None):
        logging.info("webhooks:  Bind %s to %s" % (uri_rule, method.__name__))

        for verb in methods:
            bottle_app.route(uri_rule, verb, callback=WebView(method, form_param), name=method.__name__ + '_' + verb)
        return method

    if isinstance(args[0], str):
        return lambda method: decorate(method, args[0], **kwargs)
    return decorate(args[0], '/' + args[0].__name__ + '/', **kwargs)
