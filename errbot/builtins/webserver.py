from inspect import getmembers, ismethod
import logging
import os
from threading import Thread
import urllib2
import simplejson
from simplejson.decoder import JSONDecodeError

from werkzeug.serving import ThreadedWSGIServer
from werkzeug.wsgi import SharedDataMiddleware

from flask.views import View
from flask import Flask, request, send_file, redirect, Response

from errbot import holder
from errbot import botcmd
from errbot import BotPlugin
from errbot.utils import mess_2_embeddablehtml
from errbot.version import VERSION
from errbot.plugin_manager import get_all_active_plugin_objects
from errbot.bundled.exrex import generate

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

    def decorate(method, uri_rule, methods=('POST',), form_param=None):
        logging.info("webhooks:  Bind %s to %s" % (uri_rule, method.__name__))

        for rule in holder.flask_app.url_map._rules:
            if rule.rule == uri_rule:
                holder.flask_app.view_functions[rule.endpoint] = WebView.as_view(method.__name__, method, form_param) # in case of reload just update the view fonction reference
                return method

        holder.flask_app.add_url_rule(uri_rule, view_func=WebView.as_view(method.__name__, method, form_param), methods=methods)
        return method

    if isinstance(args[0], basestring):
        return lambda method: decorate(method, args[0], **kwargs)
    return decorate(args[0], '/' + args[0].__name__ + '/', **kwargs)


class Webserver(BotPlugin):
    min_err_version = VERSION # don't copy paste that for your plugin, it is just because it is a bundled plugin !
    max_err_version = VERSION

    webserver_thread = None
    server = None
    webchat_mode = False

    def run_webserver(self):
        try:
            host = self.config['HOST']
            port = self.config['PORT']
            logging.info('Starting the webserver on %s:%i' % (host, port))

            if self.webchat_mode:
                # EVERYTHING NEEDS TO BE IN THE SAME THREAD OTHERWISE Socket.IO barfs
                try:
                    from socketio import socketio_manage
                    from socketio.namespace import BaseNamespace
                    from socketio.mixins import RoomsMixin, BroadcastMixin
                except ImportError:
                    logging.exception("Could not start the webchat view")
                    logging.error("""
                    If you intend to use the webchat view please install gevent-socketio:
                    pip install gevent-socketio
                    """)

                class ChatNamespace(BaseNamespace, RoomsMixin, BroadcastMixin):
                    def on_nickname(self, nickname):
                        self.environ.setdefault('nicknames', []).append(nickname)
                        self.socket.session['nickname'] = nickname
                        self.broadcast_event('announcement', '%s has connected' % nickname)
                        self.broadcast_event('nicknames', self.environ['nicknames'])
                        # Just have them join a default-named room
                        self.join('main_room')

                    def on_user_message(self, msg):
                        self.emit_to_room('main_room', 'msg_to_room', self.socket.session['nickname'], msg)
                        message = holder.bot.build_message(msg)
                        message.setType('groupchat') # really important for security reasons
                        message.setFrom(self.socket.session['nickname']+ '@'+host)
                        message.setTo(holder.bot.jid)
                        holder.bot.callback_message(holder.bot.conn, message)

                    def recv_message(self, message):
                        print "PING!!!", message


                @holder.flask_app.route('/')
                def index():
                    return redirect('/chat.html')

                @holder.flask_app.route("/socket.io/<path:path>")
                def run_socketio(path):
                    socketio_manage(request.environ, {'': ChatNamespace})

                holder.flask_app = SharedDataMiddleware(holder.flask_app, {
                    '/': os.path.join(os.path.dirname(__file__), 'web-static')
                })

                from socketio.server import SocketIOServer

                self.server = SocketIOServer((host, port), holder.flask_app, namespace="socket.io", policy_server=False)
            else:
                self.server = ThreadedWSGIServer(host, port, holder.flask_app)
            self.server.serve_forever()
            logging.debug('Webserver stopped')
        except Exception as e:
            logging.exception('The webserver exploded.')

    def get_configuration_template(self):
        return {'HOST': '0.0.0.0', 'PORT': 3141, 'EXTRA_FLASK_CONFIG': None, 'WEBCHAT': False}

    def activate(self):
        if not self.config:
            logging.info('Webserver is not configured. Forbid activation')
            return
        if self.config['EXTRA_FLASK_CONFIG']:
            holder.flask_app.config.update(self.config['EXTRA_FLASK_CONFIG'])

        self.webchat_mode = self.config['WEBCHAT']

        if self.webserver_thread:
            raise Exception('Invalid state, you should not have a webserver already running.')
        self.webserver_thread = Thread(target=self.run_webserver, name='Webserver Thread')
        self.webserver_thread.start()
        super(Webserver, self).activate()

    def deactivate(self):
        logging.debug('Sending signal to stop the webserver')
        if self.server:
            if isinstance(self.server, ThreadedWSGIServer):
                logging.info('webserver is ThreadedWSGIServer')
                self.server.shutdown()
                logging.info('Waiting for the webserver to terminate...')
                self.webserver_thread.join()
                logging.info('Webserver thread died as expected.')
            else:
                logging.info('webserver is SocketIOServer')
                self.server.kill() # it kills it but doesn't free the thread, I have to let it leak. [reported upstream]
        self.webserver_thread = None
        self.server = None
        super(Webserver, self).deactivate()

    @botcmd(template='webstatus')
    def webstatus(self, mess, args):
        """
        Gives a quick status of what is mapped in the internal webserver
        """
        return {'rules': (((rule.rule, rule.endpoint) for rule in holder.flask_app.url_map.iter_rules()))}

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
        for rule in holder.flask_app.url_map.iter_rules():
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

                    response = client.post(generated_url, data=content, content_type=contenttype)
                    return TEST_REPORT % (rule.rule, generated_url, contenttype, response.status_code)
        return 'Could not find endpoint %s. Check with !webstatus which endpoints are deployed' % endpoint

    def emit_mess_to_webroom(self, mess):
        if hasattr(mess, 'getBody') and mess.getBody() and not mess.getBody().isspace():
            content, is_html = mess_2_embeddablehtml(mess)
            if not is_html:
                content = '<pre>' + content + '</pre>'
            else:
                content = '<div>' + content + '</div>'
            pkt = dict(type="event",
                       name='msg_to_room',
                       args=(mess.getFrom().getNode(), content),
                       endpoint='')
            room_name = '_main_room'
            for sessid, socket in self.server.sockets.iteritems():
                if 'rooms' not in socket.session:
                    continue
                if room_name in socket.session['rooms']:
                    socket.send_packet(pkt)

    def callback_message(self, conn, mess):
        if mess.getFrom().getDomain() != self.config['HOST']: # TODO FIXME this is too ugly
            self.emit_mess_to_webroom(mess)

    def callback_botmessage(self, mess):
        if self.webchat_mode:
            self.emit_mess_to_webroom(mess)