from inspect import getmembers, ismethod
from json import loads
import logging

from bottle import Bottle, request
# noinspection PyUnresolvedReferences
from bottle import jinja2_view as view
# noinspection PyUnresolvedReferences
from bottle import jinja2_template as template

log = logging.getLogger(__name__)


class DynamicBottle(Bottle):
    def del_route(self, route_name):
        deleted_route = None
        for route_ in self.routes[:]:
            if route_.name == route_name:
                self.routes.remove(route_)
                deleted_route = route_
                break
        if not deleted_route:
            raise ValueError('Cannot find the route %s to delete' % route_name)
        del (self.router.rules[deleted_route.rule])


bottle_app = DynamicBottle()

route = bottle_app.route  # make that the default


def try_decode_json(req):
    data = req.body.read().decode()
    try:
        return loads(data)
    except Exception:
        return None


def reset_app():
    """Zap everything here, useful for unit tests
    """
    global bottle_app
    bottle_app = DynamicBottle()


class WebView(object):
    def __init__(self, func, form_param, raw):
        if form_param is not None and raw:
            raise Exception("Incompatible parameters: form_param cannot be set if raw is True")
        self.func = func
        self.raw = raw
        self.form_param = form_param
        self.method_filter = lambda obj: ismethod(obj) and self.func.__name__ == obj.__name__

    def __call__(self, *args, **kwargs):
        name_to_find = self.func.__name__
        log.debug('All active plugin objects %s ' % self.plugin_manager.get_all_active_plugin_objects())
        # Horrible hack to find the bound method from the unbound function the decorator
        # was able to give us:
        for obj in self.plugin_manager.get_all_active_plugin_objects():
            matching_members = getmembers(obj, self.method_filter)
            log.debug('Matching members %s -> %s' % (obj, matching_members))
            if matching_members:
                name, func = matching_members[0]
                if self.raw:  # override and gives the request directly
                    response = func(request, **kwargs)
                elif self.form_param:
                    content = request.forms.get(self.form_param)
                    if content is None:
                        raise Exception("Received a request on a webhook with a form_param defined, "
                                        "but that key ({}) is missing from the request.".format(self.form_param))
                    try:
                        content = loads(content)
                    except ValueError:
                        log.debug('The form parameter is not JSON, return it as a string')
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
