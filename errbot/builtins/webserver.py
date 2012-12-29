import logging
from threading import Thread

from errbot import holder
from errbot import botcmd
from errbot import BotPlugin
from errbot.version import VERSION
from errbot.builtins.wsview import bottle_app, webhook, reset_app
from bottle import run as bottle_run

TEST_REPORT = """*** Test Report
Found the matching rule : %s
Generated URL : %s
Detected your post as : %s
Status code : %i
"""


class Webserver(BotPlugin):
    min_err_version = VERSION  # don't copy paste that for your plugin, it is just because it is a bundled plugin !
    max_err_version = VERSION

    def __init__(self):
        self.webserver_thread = None
        self.webchat_mode = False
        self.ssl_context = None
        super(Webserver, self).__init__()

    def _tuple_to_ssl_context(self, tuple_):
        """Turn a (certificate, key) tuple into an SSL context for werkzeug"""
        assert len(tuple_) == 2
        from OpenSSL import SSL
        context = SSL.Context(SSL.SSLv23_METHOD)
        context.use_privatekey_file(tuple_[1])
        context.use_certificate_file(tuple_[0])
        return context

    def run_webserver(self):
        #noinspection PyBroadException
        try:
            host = self.config['HOST']
            port = self.config['PORT']
            #ssl_context = self.ssl_context
            logging.info('Starting the webserver on %s:%i' % (host, port))
            bottle_run(bottle_app, host=host, port=port)
            logging.debug('Webserver stopped')
        except KeyboardInterrupt as _:
            logging.exception('Keyboard interrupt, request a global shutdown.')
            holder.bot.shutdown()
        except Exception as _:
            logging.exception('The webserver exploded.')
            self.warn_admins("There's an issue with the webserver: %s" % _)

    def get_configuration_template(self):
        return {'HOST': '0.0.0.0', 'PORT': 3141, 'SSL': None}

    def check_configuration(self, configuration):
        super(Webserver, self).check_configuration(configuration)

        # ssl = configuration['SSL']
        # ssl_type = type(ssl)
        # ssl_error_message = "SSL must be None, a Tuple ('/path/to/certificate', '/path/to/key') or the string \"adhoc\""
        # if ssl_type not in (NoneType, TupleType, StringType):
        #    raise ValidationException(ssl_error_message)
        #if ssl is not None and (ssl_type == StringType and ssl != "adhoc" or
        #                        ssl_type == TupleType and len(ssl) != 2):
        #    raise ValidationException(ssl_error_message)

    def activate(self):
        if not self.config:
            logging.info('Webserver is not configured. Forbid activation')
            return

#        ssl = self.config['SSL']
#        if ssl is not None:
#            if type(ssl) == StringType:
#                # check_configuration will have made sure it contains a valid string
#                # so we can assign this directly
#                self.ssl_context = ssl
#            # Assume check_configuration did it's job, so it can only be a tuple if not a string
#            else:
#                # Werkzeug docs say a tuple with (cert, key) is directly supported by ssl_context
#                # but I found this to not be true. These docs were for 0.9-dev while I had 0.8.3
#                # at the time of this writing, so maybe that is new with 0.9.
#                # I couldn't find docs specific to 0.8 to verify though, but regardless, we'll have
#                # to do it the manual way.
#                try:
#                    self.ssl_context = self._tuple_to_ssl_context(ssl)
#                except ImportError:
#                    logging.error("Couldn't import from OpenSSL, aborting Webserver activation")
#                    self.warn_admins("You need to have Python bindings for OpenSSL installed "
#                                     "in order to use SSL-enabled webhooks. Aborting!")
#                    return

        if not self.webserver_thread:
            self.webserver_thread = Thread(target=self.run_webserver, name='Webserver Thread')
            self.webserver_thread.start()
        super(Webserver, self).activate()
        logging.info('Webserver activated')

    def deactivate(self):
        logging.debug('Sending signal to stop the webserver')
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
        logging.debug(repr(incoming_request))
        return repr(incoming_request)

    #noinspection PyUnusedLocal
#    @botcmd(split_args_with=' ')
#    def webhook_test(self, mess, args):
#        """
#            Test your webhooks from within err.
#
#        The syntax is :
#        !webhook test [name of the endpoint] [post content]
#
#        It triggers the notification and generate also a little test report.
#        You can get the list of the currently deployed endpoints with !webstatus
#        """
#        endpoint = args[0]
#        content = ' '.join(args[1:])
#        for rule in holder.flask_app.url_map.iter_rules():
#            if endpoint == rule.endpoint:
#                with holder.flask_app.test_client() as client:
#                    logging.debug('Found the matching rule : %s' % rule.rule)
#                    generated_url = generate(rule.rule, 1).next()  # generate a matching url from the pattern
#                    logging.debug('Generated URL : %s' % generated_url)
#
#                    # try to guess the content-type of what has been passed
#                    try:
#                        # try if it is plain json
#                        loads(content)
#                        contenttype = 'application/json'
#                    except ValueError:
#                        # try if it is a form
#                        splitted = content.split('=')
#                        #noinspection PyBroadException
#                        try:
#                            payload = '='.join(splitted[1:])
#                            loads(urllib2.unquote(payload))
#                            contenttype = 'application/x-www-form-urlencoded'
#                        except Exception as e:
#                            contenttype = 'text/plain'  # dunno what it is
#
#                    logging.debug('Detected your post as : %s' % contenttype)
#
#                    response = client.post(generated_url, data=content, content_type=contenttype)
#                    return TEST_REPORT % (rule.rule, generated_url, contenttype, response.status_code)
#        return 'Could not find endpoint %s. Check with !webstatus which endpoints are deployed' % endpoint
