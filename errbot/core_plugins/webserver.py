import sys
import os
from json import loads
from random import randrange
from threading import Thread

from webtest import TestApp
from errbot.core_plugins import flask_app
from werkzeug.serving import ThreadedWSGIServer

from errbot import botcmd, BotPlugin, webhook

from urllib.request import unquote

from OpenSSL import crypto

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
    cert.set_serial_number(randrange(1, sys.maxsize))
    cert.gmtime_adj_notBefore(0)
    cert.gmtime_adj_notAfter(60 * 60 * 24 * 365)

    subject = cert.get_subject()
    subject.CN = '*'
    setattr(subject, 'O', 'Self-Signed Certificate for Errbot')  # Pep8 annoyance workaround

    issuer = cert.get_issuer()
    issuer.CN = 'Self-proclaimed Authority'
    setattr(issuer, 'O', 'Self-Signed')  # Pep8 annoyance workaround

    pkey = crypto.PKey()
    pkey.generate_key(crypto.TYPE_RSA, 4096)
    cert.set_pubkey(pkey)
    cert.sign(pkey, 'sha256')

    f = open(cert_path, 'w')
    f.write(crypto.dump_certificate(crypto.FILETYPE_PEM, cert).decode('utf-8'))
    f.close()

    f = open(key_path, 'w')
    f.write(crypto.dump_privatekey(crypto.FILETYPE_PEM, pkey).decode('utf-8'))
    f.close()


class Webserver(BotPlugin):

    def __init__(self, *args, **kwargs):
        self.server = None
        self.server_thread = None
        self.ssl_context = None
        self.test_app = TestApp(flask_app)
        super().__init__(*args, **kwargs)

    def get_configuration_template(self):
        return {'HOST': '0.0.0.0',
                'PORT': 3141,
                'SSL': {'enabled': False,
                        'host': '0.0.0.0',
                        'port': 3142,
                        'certificate': '',
                        'key': ''}}

    def check_configuration(self, configuration):
        # it is a pain, just assume a default config if SSL is absent or set to None
        if configuration.get('SSL', None) is None:
            configuration['SSL'] = {'enabled': False, 'host': '0.0.0.0', 'port': 3142, 'certificate': '', 'key': ''}
        super().check_configuration(configuration)

    def activate(self):
        if not self.config:
            self.log.info('Webserver is not configured. Forbid activation')
            return

        if self.server_thread and self.server_thread.is_alive():
            raise Exception('Invalid state, you should not have a webserver already running.')
        self.server_thread = Thread(target=self.run_server, name='Webserver Thread')
        self.server_thread.start()
        self.log.debug('Webserver started.')

        super().activate()

    def deactivate(self):
        if self.server is not None:
            self.log.info('Shutting down the internal webserver.')
            self.server.shutdown()
            self.log.info('Waiting for the webserver thread to quit.')
            self.server_thread.join()
            self.log.info('Webserver shut down correctly.')
        super().deactivate()

    def run_server(self):
        try:
            host = self.config['HOST']
            port = self.config['PORT']
            ssl = self.config['SSL']
            self.log.info('Starting the webserver on %s:%i', host, port)
            ssl_context = (ssl['certificate'], ssl['key']) if ssl['enabled'] else None
            self.server = ThreadedWSGIServer(host, ssl['port'] if ssl_context else port, flask_app,
                                             ssl_context=ssl_context)
            self.server.serve_forever()
            self.log.debug('Webserver stopped')
        except KeyboardInterrupt:
            self.log.info('Keyboard interrupt, request a global shutdown.')
            self.server.shutdown()
        except Exception:
            self.log.exception('The webserver exploded.')

    @botcmd(template='webstatus')
    def webstatus(self, msg, args):
        """
        Gives a quick status of what is mapped in the internal webserver
        """
        return {'rules': (((rule.rule, rule.endpoint) for rule in flask_app.url_map._rules))}

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
        url = args[0]
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

        self.log.debug('Detected your post as : %s.', contenttype)

        response = self.test_app.post(url, params=content, content_type=contenttype)
        return TEST_REPORT % (url, contenttype, response.status_code)

    @botcmd(admin_only=True)
    def generate_certificate(self, _, args):
        """
        Generate a self-signed SSL certificate for the Webserver
        """
        yield ('Generating a new private key and certificate. This could take a '
               'while if your system is slow or low on entropy')
        key_path = os.sep.join((self.bot_config.BOT_DATA_DIR, "webserver_key.pem"))
        cert_path = os.sep.join((self.bot_config.BOT_DATA_DIR, "webserver_certificate.pem"))
        make_ssl_certificate(key_path=key_path, cert_path=cert_path)
        yield f'Certificate successfully generated and saved in {self.bot_config.BOT_DATA_DIR}.'

        suggested_config = self.config
        suggested_config['SSL']['enabled'] = True
        suggested_config['SSL']['host'] = suggested_config['HOST']
        suggested_config['SSL']['port'] = suggested_config['PORT'] + 1
        suggested_config['SSL']['key'] = key_path
        suggested_config['SSL']['certificate'] = cert_path
        yield 'To enable SSL with this certificate, the following config is recommended:'
        yield f'{suggested_config!r}'
