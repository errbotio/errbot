from inspect import getmembers, ismethod
import logging
from threading import Thread
import urllib2
from errbot import holder
import simplejson
from simplejson.decoder import JSONDecodeError
from werkzeug.serving import ThreadedWSGIServer

from errbot import botcmd
from errbot import BotPlugin
from errbot.version import VERSION
from errbot.plugin_manager import get_all_active_plugin_objects
from errbot.bundled.exrex import generate

from flask.views import View
from flask import request
from flask import Response

OK = Response()

TEST_REPORT = """*** Test Report
Found the matching rule : %s
Generated URL : %s
Detected your post as : %s
Status code : %i
"""

class WebView(View):
    def __init__(self, func, form_param):
        self.func = func
        self.form_param = form_param

    def dispatch_request(self):
        for obj in get_all_active_plugin_objects(): # horrible hack to find back the bound method from the unbound function the decorator was able to give us
            for name, method in getmembers(obj, ismethod):
                if method.im_func.__name__ == self.func.__name__: # FIXME : add a fully qualified name here
                    if self.form_param:
                        content = request.form[self.form_param]
                        try:
                            content = simplejson.loads(content)
                        except JSONDecodeError:
                            logging.debug('The form parameter is not JSON, return it as a string')
                        response = self.func(obj, content)
                    else:
                        response = self.func(obj, request.json if request.json else request.data) # flask will find out automagically if it is a JSON structure
                    return response if response else OK # assume None as an OK response (simplifies the client side)

        raise Exception('Problem finding back the correct Handlerfor func %s', self.func)
def webhook(*args, **kwargs):
    """
        Simple shortcut for the plugins to be notified on webhooks
    """
    def decorate(method, uri_rule, methods=('POST',), form_param = None):
        logging.info("webhooks:  Bind %s to %s" % (uri_rule, method.__name__))

        for rule in holder.flask_app.url_map._rules:
            if rule.rule == uri_rule:
                holder.flask_app.view_functions[rule.endpoint] = WebView.as_view(method.__name__, method, form_param) # in case of reload just update the view fonction reference
                return method

        holder.flask_app.add_url_rule(uri_rule, view_func=WebView.as_view(method.__name__, method, form_param), methods = methods)
        return method

    if isinstance(args[0], basestring):
        return lambda method: decorate(method, args[0], **kwargs)
    return decorate(args[0], '/' + args[0].__name__ + '/', **kwargs)



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
        """
        Gives a quick status of what is mapped in the internal webserver
        """
        return '\n'.join((rule.rule + " -> " + rule.endpoint for rule in holder.flask_app.url_map.iter_rules()))

    @botcmd(split_args_with=' ')
    def webhook_test(self, mess, args):
        """
            Test your webhooks from within err.

        The syntax is :
        !webhook test [name of the endpoint] [post content]

        It triggers the notification and generate also a little test report.
        You can get the list of the currently deployed endpoints with !webstatus
        """
        endpoint = args[0]
        content = ' '.join(args[1:])
        for rule in  holder.flask_app.url_map.iter_rules():
            if endpoint == rule.endpoint:
                with holder.flask_app.test_client() as client:
                    logging.debug('Found the matching rule : %s' % rule.rule)
                    generated_url = generate(rule.rule, 1).next() # generate a matching url from the pattern
                    logging.debug('Generated URL : %s' % generated_url)

                    # try to guess the content-type of what has been passed
                    try:
                        # try if it is plain json
                        simplejson.loads(content)
                        contenttype = 'application/json'
                    except JSONDecodeError:
                        # try if it is a form
                        splitted = content.split('=')
                        try:
                            payload = '='.join(splitted[1:])
                            simplejson.loads(urllib2.unquote(payload))
                            contenttype = 'application/x-www-form-urlencoded'
                        except Exception as e:
                            contenttype = 'text/plain' # dunno what it is

                    logging.debug('Detected your post as : %s' % contenttype)

                    response = client.post(generated_url, data=content, content_type = contenttype)
                    return TEST_REPORT %(rule.rule, generated_url, contenttype, response.status_code)
        return 'Could not find endpoint %s. Check with !webstatus which endpoints are deployed' % endpoint


    @webhook(r'/zourby/')
    def zourby(self, incoming_request):
        logging.debug(type(incoming_request))
        logging.debug(str(incoming_request))
        return str(holder.bot.status(None, None))

