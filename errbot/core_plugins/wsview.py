from inspect import getmembers, ismethod
from json import loads
import logging

from bottle import Bottle, request

# noinspection PyUnresolvedReferences
from bottle import jinja2_view as view
# noinspection PyUnresolvedReferences
from bottle import jinja2_template as template

log = logging.getLogger(__name__)


def strip_path():
    # strip the trailing slashes on incoming requests
    request.environ['PATH_INFO'] = request.environ['PATH_INFO'].rstrip('/')


class DynamicBottle(Bottle):

    def __init__(self, catchall=True, autojson=True):
        super().__init__(catchall, autojson)
        self.add_hook('before_request', strip_path)

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


def route(obj):
    """Check for functions to route in obj and route them."""
    classname = obj.__class__.__name__
    log.info("Checking %s for webhooks", classname)
    for name, func in getmembers(obj, ismethod):
        if getattr(func, '_err_webhook_uri_rule', False):
            log.info("Webhook routing %s", func.__name__)
            for verb in func._err_webhook_methods:
                wv = WebView(func,
                             func._err_webhook_form_param,
                             func._err_webhook_raw)
                bottle_app.route(func._err_webhook_uri_rule, verb,
                                 callback=wv, name=func.__name__ + '_' + verb)


class WebView(object):
    def __init__(self, func, form_param, raw):
        if form_param is not None and raw:
            raise Exception("Incompatible parameters: form_param cannot be set if raw is True")
        self.func = func
        self.raw = raw
        self.form_param = form_param
        self.method_filter = lambda obj: ismethod(obj) and self.func.__name__ == obj.__name__

    def __call__(self, *args, **kwargs):
        if self.raw:  # override and gives the request directly
            response = self.func(request, **kwargs)
        elif self.form_param:
            content = request.forms.get(self.form_param)
            if content is None:
                raise Exception("Received a request on a webhook with a form_param defined, "
                                "but that key ({}) is missing from the request.".format(self.form_param))
            try:
                content = loads(content)
            except ValueError:
                log.debug('The form parameter is not JSON, return it as a string')
            response = self.func(content, **kwargs)
        else:
            data = try_decode_json(request)
            if not data:
                if hasattr(request, 'forms'):
                    data = dict(request.forms)  # form encoded
                else:
                    data = request.body.read().decode()
            response = self.func(data, **kwargs)
        return response if response else ''  # assume None as an OK response (simplifies the client side)
