import logging
from threading import Thread

from errbot import holder
from errbot import botcmd
from errbot import BotPlugin
from errbot.version import VERSION
from errbot.builtins.wsview import bottle_app, webhook, reset_app
from rocket import Rocket

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

    def run_webserver(self):
        #noinspection PyBroadException
        try:
            host = self.config['HOST']
            port = self.config['PORT']
            logging.info('Starting the webserver on %s:%i' % (host, port))
            rocket = Rocket(interfaces=(host, port),
                            method='wsgi',
                            app_info={'wsgi_app': bottle_app},
                           )
            rocket.start()
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
        # Doing a loop on one item seems silly, but this used to be a bigger dictionary.
        # Keeping the code makes it easy to add new items again in the future.
        for k,v in dict(SSL=None).items():
            if k not in configuration: configuration[k] = v
        super(Webserver, self).check_configuration(configuration)

    def activate(self):
        if not self.config:
            logging.info('Webserver is not configured. Forbid activation')
            return

        if not self.webserver_thread:
            self.webserver_thread = Thread(target=self.run_webserver, name='Webserver Thread')
            self.webserver_thread.setDaemon(True)
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
