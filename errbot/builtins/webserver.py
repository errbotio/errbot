from inspect import getmembers, ismethod
import logging
from threading import Thread
from errbot import holder
from errbot.botplugin import BotPlugin
from errbot.version import VERSION
from flask.views import View
from flask import request
from flask import Response
from werkzeug.serving import ThreadedWSGIServer
from errbot.plugin_manager import get_all_active_plugin_objects
from errbot.jabberbot import botcmd
OK = Response()

class WebView(View):
    def __init__(self, func):
        self.func = func

    def dispatch_request(self):
        for obj in get_all_active_plugin_objects(): # horrible hack to find back the bound method from the unbound function the decorator was able to give us
            for name, method in getmembers(obj, ismethod):
                if method.im_func.__name__ == self.func.__name__: # FIXME : add a fully qualified name here
                    response = self.func(obj, request.json if request.json else request.data) # flask will find out automagically if it is a JSON structure
                    return response if response else OK # assume None as an OK response (simplifies the client side)

        raise Exception('Problem finding back the correct Handlerfor func %s', self.func)
def webhook(*args, **kwargs):
    """
        Simple shortcut for the plugins to be notified on webhooks
    """
    logging.info("webhooks:  Bind %s to %s" % (args, kwargs))
    def decorate(method, uri_rule, methods=('POST',)):
        logging.info("decorate:  Bind %s to %s" % (uri_rule, method.__name__))

        for rule in holder.flask_app.url_map._rules:
            if rule.rule == uri_rule:
                holder.flask_app.view_functions[rule.endpoint] = WebView.as_view(method.__name__, method) # in case of reload just update the view fonction reference
                return method

        holder.flask_app.add_url_rule(uri_rule, view_func=WebView.as_view(method.__name__, method), methods = methods)
        return method

    if not len(args):
        raise Exception('You need to at least pass the uri rule pattern you webhook will answer to')
    return lambda method: decorate(method, args[0], **kwargs)


class Webserver(BotPlugin):
    min_err_version = VERSION # don't copy paste that for your plugin, it is just because it is a bundled plugin !
    max_err_version = VERSION

    webserver_thread = None
    server = None

    def run_webserver(self):
        try:
            host = self.config['HOST']
            port = self.config['PORT']
            logging.info('Starting the webserver on %s:%i' % (host, port))
            self.server = ThreadedWSGIServer(host, port, holder.flask_app)
            self.server.serve_forever()
            logging.debug('Webserver stopped')
        except Exception as e:
            logging.exception('The webserver exploded.')

    def get_configuration_template(self):
        return {'HOST': '0.0.0.0', 'PORT': 3141, 'EXTRA_FLASK_CONFIG': None}

    def activate(self):
        if not self.config:
            logging.info('Webserver is not configured. Forbid activation')
            return
        if self.config['EXTRA_FLASK_CONFIG']:
            holder.flask_app.config.update(self.config['EXTRA_FLASK_CONFIG'])
        if self.webserver_thread:
            raise Exception('Invalid state, you should not have a webserver already running.')
        self.webserver_thread = Thread(target=self.run_webserver)
        self.webserver_thread.start()
        super(Webserver, self).activate()

    def deactivate(self):
        logging.debug('Sending signal to stop the webserver')
        self.server.shutdown()
        logging.info('Waiting for the webserver to terminate...')
        self.webserver_thread.join()
        logging.info('Webserver thread died as expected.')
        self.webserver_thread = None
        self.server = None
        super(Webserver, self).deactivate()

    @botcmd
    def webstatus(self, mess, args):
        return '\n'.join((rule.rule + "->" + rule.endpoint for rule in holder.flask_app.url_map.iter_rules()))

    @webhook(r'/test/')
    def test_method(self, incoming_request):
        logging.debug(type(incoming_request))
        logging.debug(str(incoming_request))
        return str(holder.bot.status(None, None))

