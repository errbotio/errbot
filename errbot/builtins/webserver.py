from json import loads
import logging
from threading import Thread

from errbot import holder, PY3
from errbot import botcmd
from errbot import BotPlugin
from errbot.version import VERSION
from errbot.builtins.wsview import bottle_app, webhook
from errbot.bundled.rocket import Rocket
from webtest import TestApp

if PY3:
    from urllib.request import unquote
else:
    from urllib2 import unquote

TEST_REPORT = """*** Test Report
URL : %s
Detected your post as : %s
Status code : %i
"""


class Webserver(BotPlugin):
    min_err_version = VERSION  # don't copy paste that for your plugin, it is just because it is a bundled plugin !
    max_err_version = VERSION

    def __init__(self):
        self.webserver = None
        self.webchat_mode = False
        self.ssl_context = None
        self.test_app = TestApp(bottle_app)
        super(Webserver, self).__init__()

    def get_configuration_template(self):
        return {'HOST': '0.0.0.0',
                'PORT': 3141,
                'SSL': {'enabled': False,
                        'host': '0.0.0.0',
                        'port': 3142,
                        'certificate': "",
                        'key': ""}}

    def check_configuration(self, configuration):
        # it is a pain, just assume a default config if SSL is absent or set to None
        if configuration.get('SSL', None) is None:
            configuration['SSL'] = {'enabled': False, 'host': '0.0.0.0', 'port': 3142, 'certificate': "", 'key': ""}
        super(Webserver, self).check_configuration(configuration)

    def activate(self):
        if not self.config:
            logging.info('Webserver is not configured. Forbid activation')
            return

        host = self.config['HOST']
        port = self.config['PORT']
        ssl = self.config['SSL']
        interfaces = [(host, port)]
        if ssl['enabled']:
            interfaces.append((ssl['host'], ssl['port'], ssl['key'], ssl['certificate']))
        logging.info('Firing up the Rocket')
        self.webserver = Rocket(interfaces=interfaces,
                                app_info={'wsgi_app': bottle_app}, )
        self.webserver.start(background=True)
        logging.debug('Liftoff!')

        super(Webserver, self).activate()
        logging.info('Webserver activated')

    def deactivate(self):
        if self.webserver is not None:
            logging.debug('Sending signal to stop the webserver')
            self.webserver.stop()
        super(Webserver, self).deactivate()

    #noinspection PyUnusedLocal
    @botcmd(template='webstatus')
    def webstatus(self, mess, args):
        """
        Gives a quick status of what is mapped in the internal webserver
        """
        return {'rules': (((route.rule, route.name) for route in bottle_app.routes))}

    @webhook
    def echo(self, incoming_request):
        """
        A simple test webhook
        """
        logging.debug("Your incoming request is :" + str(incoming_request))
        return str(incoming_request)

    @botcmd(split_args_with=' ')
    def webhook_test(self, _, args):
        """
            Test your webhooks from within err.

        The syntax is :
        !webhook test [relative_url] [post content]

        It triggers the notification and generate also a little test report.
        """
        url = args[0] if PY3 else args[0].encode()  # PY2 needs a str not unicode
        content = ' '.join(args[1:])

        # try to guess the content-type of what has been passed
        try:
            # try if it is plain json
            loads(content)
            contenttype = 'application/json'
        except ValueError:
            # try if it is a form
            splitted = content.split('=')
            #noinspection PyBroadException
            try:
                payload = '='.join(splitted[1:])
                loads(unquote(payload))
                contenttype = 'application/x-www-form-urlencoded'
            except Exception as _:
                contenttype = 'text/plain'  # dunno what it is

        logging.debug('Detected your post as : %s' % contenttype)

        response = self.test_app.post(url, params=content, content_type=contenttype)
        return TEST_REPORT % (url, contenttype, response.status_code)
