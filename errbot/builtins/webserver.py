# TO BE COMPLETELY REDONE FOR PY3

#from inspect import getmembers, ismethod
#import logging
#import os
#from threading import Thread
#import urllib
#from json import loads
#
#from werkzeug.serving import ThreadedWSGIServer
#from werkzeug.wsgi import SharedDataMiddleware
#
#from errbot import holder
#from errbot import botcmd
#from errbot import BotPlugin
#from errbot.utils import mess_2_embeddablehtml, recurse_check_structure, ValidationException
#from errbot.version import VERSION
#from errbot.plugin_manager import get_all_active_plugin_objects
#from errbot.bundled.exrex import generate
#from errbot.builtins.wsview import WebView
#from wsview import OK, webhook
#
#from types import *
#
#TEST_REPORT = """*** Test Report
#Found the matching rule : %s
#Generated URL : %s
#Detected your post as : %s
#Status code : %i
#"""
#
#
#class Webserver(BotPlugin):
#    min_err_version = VERSION  # don't copy paste that for your plugin, it is just because it is a bundled plugin !
#    max_err_version = VERSION
#
#    webserver_thread = None
#    server = None
#    webchat_mode = False
#    ssl_context = None
#
#    def _tuple_to_ssl_context(self, tuple_):
#        """Turn a (certificate, key) tuple into an SSL context for werkzeug"""
#        assert len(tuple_) == 2
#        from OpenSSL import SSL
#        context = SSL.Context(SSL.SSLv23_METHOD)
#        context.use_privatekey_file(tuple_[1])
#        context.use_certificate_file(tuple_[0])
#        return context
#
#    def run_webserver(self):
#        #noinspection PyBroadException
#        try:
#            host = self.config['HOST']
#            port = self.config['PORT']
#            ssl_context = self.ssl_context
#            logging.info('Starting the webserver on %s:%i' % (host, port))
#            if self.webchat_mode:
#                # EVERYTHING NEEDS TO BE IN THE SAME THREAD OTHERWISE Socket.IO barfs
#                try:
#                    from socketio import socketio_manage
#                    from socketio.namespace import BaseNamespace
#                    from socketio.mixins import RoomsMixin, BroadcastMixin
#
#                    class ChatNamespace(BaseNamespace, RoomsMixin, BroadcastMixin):
#                        def on_nickname(self, nickname):
#                            self.environ.setdefault('nicknames', []).append(nickname)
#                            self.socket.session['nickname'] = nickname
#                            self.broadcast_event('announcement', '%s has connected' % nickname)
#                            self.broadcast_event('nicknames', self.environ['nicknames'])
#                            # Just have them join a default-named room
#                            self.join('main_room')
#
#                        def on_user_message(self, msg):
#                            self.emit_to_room('main_room', 'msg_to_room', self.socket.session['nickname'], msg)
#                            message = holder.bot.build_message(msg)
#                            message.setType('groupchat')  # really important for security reasons
#                            message.setFrom(self.socket.session['nickname'] + '@' + host)
#                            message.setTo(holder.bot.jid)
#                            holder.bot.callback_message(holder.bot.conn, message)
#
#                        def recv_message(self, message):
#                            print "PING!!!", message
#                except ImportError:
#                    logging.exception("Could not start the webchat view")
#                    logging.error("""
#                    If you intend to use the webchat view please install gevent-socketio:
#                    pip install gevent-socketio
#                    """)
#
#                #noinspection PyUnusedLocal
#                @holder.flask_app.route('/')
#                def index():
#                    return redirect('/chat.html')
#
#                #noinspection PyUnusedLocal
#                @holder.flask_app.route("/socket.io/<path:path>")
#                def run_socketio(path):
#                    socketio_manage(request.environ, {'': ChatNamespace})
#
#                encapsulating_middleware = SharedDataMiddleware(holder.flask_app, {
#                    '/': os.path.join(os.path.dirname(__file__), 'web-static')
#                })
#
#                from socketio.server import SocketIOServer
#
#                self.server = SocketIOServer((host, port), encapsulating_middleware, namespace="socket.io", policy_server=False)
#            else:
#                self.server = ThreadedWSGIServer(host, port, holder.flask_app, ssl_context=ssl_context)
#            self.server.serve_forever()
#            logging.debug('Webserver stopped')
#        except KeyboardInterrupt as _:
#            logging.exception('Keyboard interrupt, request a global shutdown.')
#            if isinstance(self.server, ThreadedWSGIServer):
#                logging.info('webserver is ThreadedWSGIServer')
#                self.server.shutdown()
#            else:
#                logging.info('webserver is SocketIOServer')
#                self.server.kill()
#            self.server = None
#            holder.bot.shutdown()
#        except Exception as _:
#            logging.exception('The webserver exploded.')
#
#    def get_configuration_template(self):
#        return {'HOST': '0.0.0.0', 'PORT': 3141, 'EXTRA_FLASK_CONFIG': None, 'WEBCHAT': False, 'SSL': None}
#
#    def check_configuration(self, configuration):
#        super(Webserver, self).check_configuration(configuration)
#
#        ssl = configuration['SSL']
#        ssl_type = type(ssl)
#        ssl_error_message = "SSL must be None, a Tuple ('/path/to/certificate', '/path/to/key') or the string \"adhoc\""
#        if ssl_type not in (NoneType, TupleType, StringType):
#            raise ValidationException(ssl_error_message)
#        if ssl is not None and (ssl_type == StringType and ssl != "adhoc" or
#                                ssl_type == TupleType and len(ssl) != 2):
#            raise ValidationException(ssl_error_message)
#
#    def activate(self):
#        if not self.config:
#            logging.info('Webserver is not configured. Forbid activation')
#            return
#        if self.config['EXTRA_FLASK_CONFIG']:
#            holder.flask_app.config.update(self.config['EXTRA_FLASK_CONFIG'])
#        if self.config['WEBCHAT'] and self.config['SSL'] is not None:
#            self.warn_admins("(Webserver) SSL is ignored when WEBCHAT = True")
#        self.webchat_mode = self.config['WEBCHAT']
#
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
#
#        if self.webserver_thread:
#            raise Exception('Invalid state, you should not have a webserver already running.')
#        self.webserver_thread = Thread(target=self.run_webserver, name='Webserver Thread')
#        self.webserver_thread.start()
#        super(Webserver, self).activate()
#
#    def shutdown(self):
#        if isinstance(self.server, ThreadedWSGIServer):
#            logging.info('webserver is ThreadedWSGIServer')
#            self.server.shutdown()
#            logging.info('Waiting for the webserver to terminate...')
#            self.webserver_thread.join()
#            logging.info('Webserver thread died as expected.')
#        else:
#            logging.info('webserver is SocketIOServer')
#            self.server.kill()  # it kills it but doesn't free the thread, I have to let it leak. [reported upstream]
#
#    def deactivate(self):
#        logging.debug('Sending signal to stop the webserver')
#        if self.server:
#            self.shutdown()
#        self.webserver_thread = None
#        self.server = None
#        super(Webserver, self).deactivate()
#
#    #noinspection PyUnusedLocal
#    @botcmd(template='webstatus')
#    def webstatus(self, mess, args):
#        """
#        Gives a quick status of what is mapped in the internal webserver
#        """
#        return {'rules': (((rule.rule, rule.endpoint) for rule in holder.flask_app.url_map.iter_rules()))}
#
#    #noinspection PyUnusedLocal
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
#
#    def emit_mess_to_webroom(self, mess):
#        if not self.server or not self.webchat_mode:
#            return
#
#        if hasattr(mess, 'getBody') and mess.getBody() and not mess.getBody().isspace():
#            content, is_html = mess_2_embeddablehtml(mess)
#            if not is_html:
#                content = '<pre>' + content + '</pre>'
#            else:
#                content = '<div>' + content + '</div>'
#            pkt = dict(type="event",
#                       name='msg_to_room',
#                       args=(mess.getFrom().getNode(), content),
#                       endpoint='')
#            room_name = '_main_room'
#            for sessid, socket in self.server.sockets.iteritems():
#                if 'rooms' not in socket.session:
#                    continue
#                if room_name in socket.session['rooms']:
#                    socket.send_packet(pkt)
#
#    def callback_message(self, conn, mess):
#        if mess.getFrom().getDomain() != self.config['HOST']:  # TODO FIXME this is too ugly
#            self.emit_mess_to_webroom(mess)
#
#    def callback_botmessage(self, mess):
#        self.emit_mess_to_webroom(mess)
