from inspect import getmembers, ismethod
from json import loads
import logging

from flask.app import Flask
from flask.views import View
from flask import request
import errbot.core_plugins

log = logging.getLogger(__name__)


def strip_path():
    # strip the trailing slashes on incoming requests
    request.environ['PATH_INFO'] = request.environ['PATH_INFO'].rstrip('/')


def try_decode_json(req):
    data = req.data.decode()
    try:
        return loads(data)
    except Exception:
        return None


def reset_app():
    """Zap everything here, useful for unit tests
    """
    errbot.core_plugins.flask_app = Flask(__name__)


def route(obj):
    """Check for functions to route in obj and route them."""
    flask_app = errbot.core_plugins.flask_app
    classname = obj.__class__.__name__
    log.info("Checking %s for webhooks", classname)
    for name, func in getmembers(obj, ismethod):
        if getattr(func, '_err_webhook_uri_rule', False):
            log.info("Webhook routing %s", func.__name__)
            form_param = func._err_webhook_form_param
            uri_rule = func._err_webhook_uri_rule
            verbs = func._err_webhook_methods
            raw = func._err_webhook_raw

            callable_view = WebView.as_view(func.__name__ + '_' + '_'.join(verbs), func, form_param, raw)

            # Change existing rule.
            for rule in flask_app.url_map._rules:
                if rule.rule == uri_rule:
                    flask_app.view_functions[rule.endpoint] = callable_view
                    return

            # Add a new rule
            flask_app.add_url_rule(uri_rule, view_func=callable_view, methods=verbs, strict_slashes=False)


class WebView(View):
    def __init__(self, func, form_param, raw):
        if form_param is not None and raw:
            raise Exception("Incompatible parameters: form_param cannot be set if raw is True")
        self.func = func
        self.raw = raw
        self.form_param = form_param
        self.method_filter = lambda obj: ismethod(obj) and self.func.__name__ == obj.__name__

    def dispatch_request(self, *args, **kwargs):

        if self.raw:  # override and gives the request directly
            response = self.func(request, **kwargs)
        elif self.form_param:
            content = request.form.get(self.form_param)
            if content is None:
                raise Exception('Received a request on a webhook with a form_param defined, '
                                'but that key (%s) is missing from the request.', self.form_param)
            try:
                content = loads(content)
            except ValueError:
                log.debug('The form parameter is not JSON, return it as a string.')
            response = self.func(content, **kwargs)
        else:
            data = try_decode_json(request)
            if not data:
                if hasattr(request, 'forms'):
                    data = dict(request.forms)  # form encoded
                else:
                    data = request.data.decode()
            response = self.func(data, **kwargs)
        return response if response else ''  # assume None as an OK response (simplifies the client side)
