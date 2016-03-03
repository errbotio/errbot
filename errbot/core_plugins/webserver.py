import sys
import os
from json import loads
from random import random

from webtest import TestApp

from errbot import botcmd, BotPlugin, webhook
from errbot.utils import PY3
from errbot.core_plugins.wsview import bottle_app
from rocket import Rocket

if PY3:
    from urllib.request import unquote
else:
    from urllib2 import unquote

try:
    from OpenSSL import crypto

    has_crypto = True
except ImportError:
    has_crypto = False

TEST_REPORT = """*** Test Report
URL : %s
Detected your post as : %s
Status code : %i
"""


def make_ssl_certificate(key_path, cert_path):
    """
    Generate a self-signed certificate

    The generated key will be written out to key_path, with the corresponding
    certificate itself being written to cert_path.
    :param cert_path: path where to write the certificate.
    :param key_path: path where to write the key.
    """
    cert = crypto.X509()
    cert.set_serial_number(int(random() * sys.maxsize))
    cert.gmtime_adj_notBefore(0)
    cert.gmtime_adj_notAfter(60 * 60 * 24 * 365)

    subject = cert.get_subject()
    subject.CN = '*'
    subject.O = 'Self-Signed Certificate for Err'

    issuer = cert.get_issuer()
    issuer.CN = 'Self-proclaimed Authority'
    issuer.O = 'Self-Signed'

    pkey = crypto.PKey()
    pkey.generate_key(crypto.TYPE_RSA, 4096)
    cert.set_pubkey(pkey)
    cert.sign(pkey, 'sha256' if PY3 else b'sha256')

    f = open(cert_path, 'w')
    f.write(crypto.dump_certificate(crypto.FILETYPE_PEM, cert).decode('utf-8'))
    f.close()

    f = open(key_path, 'w')
    f.write(crypto.dump_privatekey(crypto.FILETYPE_PEM, pkey).decode('utf-8'))
    f.close()


class Webserver(BotPlugin):

    def __init__(self, bot):
        self.webserver = None
        self.webchat_mode = False
        self.ssl_context = None
        self.test_app = TestApp(bottle_app)
        super().__init__(bot)

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
        super().check_configuration(configuration)

    def activate(self):
        if not self.config:
            self.log.info('Webserver is not configured. Forbid activation')
            return

        host = self.config['HOST']
        port = self.config['PORT']
        ssl = self.config['SSL']
        interfaces = [(host, port)]
        if ssl['enabled']:
            # noinspection PyTypeChecker
            interfaces.append((ssl['host'], ssl['port'], ssl['key'], ssl['certificate']))
        self.log.info('Firing up the Rocket')
        self.webserver = Rocket(interfaces=interfaces,
                                app_info={'wsgi_app': bottle_app}, )
        self.webserver.start(background=True)
        self.log.debug('Liftoff!')

        super().activate()

    def deactivate(self):
        if self.webserver is not None:
            self.log.debug('Sending signal to stop the webserver')
            self.webserver.stop()
        super().deactivate()

    # noinspection PyUnusedLocal
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
        self.log.debug("Your incoming request is :" + str(incoming_request))
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
            # noinspection PyBroadException
            try:
                payload = '='.join(splitted[1:])
                loads(unquote(payload))
                contenttype = 'application/x-www-form-urlencoded'
            except Exception as _:
                contenttype = 'text/plain'  # dunno what it is

        self.log.debug('Detected your post as : %s' % contenttype)

        response = self.test_app.post(url, params=content, content_type=contenttype)
        return TEST_REPORT % (url, contenttype, response.status_code)

    @botcmd(admin_only=True)
    def generate_certificate(self, mess, args):
        """
        Generate a self-signed SSL certificate for the Webserver
        """
        if not has_crypto:
            yield ("It looks like pyOpenSSL isn't installed. Please install this "
                   "package using for example `pip install pyOpenSSL`, then try again")
            return

        yield ("Generating a new private key and certificate. This could take a "
               "while if your system is slow or low on entropy")
        key_path = os.sep.join((self.bot_config.BOT_DATA_DIR, "webserver_key.pem"))
        cert_path = os.sep.join((self.bot_config.BOT_DATA_DIR, "webserver_certificate.pem"))
        make_ssl_certificate(key_path=key_path, cert_path=cert_path)
        yield "Certificate successfully generated and saved in {}".format(self.bot_config.BOT_DATA_DIR)

        suggested_config = self.config
        suggested_config['SSL']['enabled'] = True
        suggested_config['SSL']['host'] = suggested_config['HOST']
        suggested_config['SSL']['port'] = suggested_config['PORT'] + 1
        suggested_config['SSL']['key'] = key_path
        suggested_config['SSL']['certificate'] = cert_path
        yield ("To enable SSL with this certificate, the following config "
               "is recommended:")
        yield "{!r}".format(suggested_config)
