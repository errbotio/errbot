#!/usr/bin/python
# -*- coding: utf-8 -*-

# JabberBot: A simple jabber/xmpp bot framework
# Copyright (c) 2007-2011 Thomas Perl <thp.io/about>
# $Id: fd058dd6b4752e79cefe6b03777c127bdc987eba $
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#

"""
A framework for writing Jabber/XMPP bots and services

The JabberBot framework allows you to easily write bots
that use the XMPP protocol. You can create commands by
decorating functions in your subclass or customize the
bot's operation completely. MUCs are also supported.
"""

import os
import re
import sys
import thread
from xmpp.protocol import NS_CAPS
from xmpp.simplexml import XML2Node
from errbot.templating import tenv
from errbot.utils import get_jid_from_message
from config import BOT_ADMINS

from utils import get_sender_username

try:
    import xmpp
except ImportError:
    print >> sys.stderr, """
    You need to install xmpppy from http://xmpppy.sf.net/.
    On Debian-based systems, install the python-xmpp package.
    """
    sys.exit(-1)

import time
import inspect
import logging
import traceback
from collections import deque

# Will be parsed by setup.py to determine package metadata
__author__ = 'Thomas Perl <m@thp.io>'
__version__ = '0.14'
__website__ = 'http://thp.io/2007/python-jabberbot/'
__license__ = 'GNU General Public License version 3 or later'

HIPCHAT_PRESENCE_ATTRS = {'node': 'http://hipchat.com/client/bot', 'ver': 'v1.1.0'}



def botcmd(*args, **kwargs):
    """Decorator for bot command functions
    extra parameters to customize the command:
    name : override the command name
    thread : asynchronize the command
    split_args_with : prepare the arguments by splitting them by the given character
    """

    def decorate(func, hidden=False, name=None, thread=False, split_args_with = None, admin_only = False, historize = True, template = None):
        if not hasattr(func, '_jabberbot_command'): # don't override generated functions
            setattr(func, '_jabberbot_command', True)
            setattr(func, '_jabberbot_command_hidden', hidden)
            setattr(func, '_jabberbot_command_name', name or func.__name__)
            setattr(func, '_jabberbot_command_split_args_with', split_args_with)
            setattr(func, '_jabberbot_command_admin_only', admin_only)
            setattr(func, '_jabberbot_command_historize', historize)
            setattr(func, '_jabberbot_command_thread', thread) # Experimental!
            setattr(func, '_jabberbot_command_template', template) # Experimental!
        return func

    if len(args):
        return decorate(args[0], **kwargs)
    else:
        return lambda func: decorate(func, **kwargs)


def is_from_history(mess):
    props = mess.getProperties()
    return 'urn:xmpp:delay' in props or xmpp.NS_DELAY in props

class JabberBot(object):
    # Show types for presence
    AVAILABLE, AWAY, CHAT = None, 'away', 'chat'
    DND, XA, OFFLINE = 'dnd', 'xa', 'unavailable'

    # UI-messages (overwrite to change content)
    MSG_AUTHORIZE_ME = 'Hey there. You are not yet on my roster. '\
                       'Authorize my request and I will do the same.'
    MSG_NOT_AUTHORIZED = 'You did not authorize my subscription request. '\
                         'Access denied.'
    MSG_UNKNOWN_COMMAND = 'Unknown command: "%(command)s". '\
                          'Type "help" for available commands.'
    MSG_HELP_TAIL = 'Type help <command name> to get more info '\
                    'about that specific command.'
    MSG_HELP_UNDEFINED_COMMAND = 'That command is not defined.'
    MSG_ERROR_OCCURRED = 'Sorry for your inconvenience. '\
                         'An unexpected error occurred.'

    PING_FREQUENCY = 10 # Set to the number of seconds, e.g. 60.
    PING_TIMEOUT = 2 # Seconds to wait for a response.
    RETRY_FREQUENCY = 10 # Set to the number of seconds to attempt another connection attempt in case of connectivity loss

    MESSAGE_SIZE_LIMIT = 10000 # the default one from hipchat
    MESSAGE_SIZE_ERROR_MESSAGE = '|<- SNIP ! Message too long.'

    return_code = 0 # code for the process exit

    cmd_history = deque(maxlen=10)

    def __init__(self, username, password, res=None, debug=False,
                 privatedomain=False, acceptownmsgs=False, handlers=None):
        """Initializes the jabber bot and sets up commands.

        username and password should be clear ;)

        If res provided, res will be ressourcename,
        otherwise it defaults to classname of childclass

        If debug is True log messages of xmpppy will be printed to console.
        Logging of Jabberbot itself is NOT affected.

        If privatedomain is provided, it should be either
        True to only allow subscriptions from the same domain
        as the bot or a string that describes the domain for
        which subscriptions are accepted (e.g. 'jabber.org').

        If acceptownmsgs it set to True, this bot will accept
        messages from the same JID that the bot itself has. This
        is useful when using JabberBot with a single Jabber account
        and multiple instances that want to talk to each other.

        If handlers are provided, default handlers won't be enabled.
        Usage like: [('stanzatype1', function1), ('stanzatype2', function2)]
        Signature of function should be callback_xx(self, conn, stanza),
        where conn is the connection and stanza the current stanza in process.
        First handler in list will be served first.
        Don't forget to raise exception xmpp.NodeProcessed to stop
        processing in other handlers (see callback_presence)
        """
        # TODO sort this initialisation thematically
        self.__debug = debug
        self.log = logging.getLogger(__name__)
        self.__username = username
        self.__password = password
        self.jid = xmpp.JID(self.__username)
        self.res = (res or self.__class__.__name__)
        self.conn = None
        self.__finished = False
        self.__show = None
        self.__status = None
        self.__seen = {}
        self.__threads = {}
        self.__lastping = time.time()
        self.__privatedomain = privatedomain
        self.__acceptownmsgs = acceptownmsgs

        self.handlers = (handlers or [('message', self.callback_message),
            ('presence', self.callback_presence)])

        # Collect commands from source
        self.refresh_command_list()
        self.roster = None

    ################################


    def refresh_command_list(self):
        self.commands = {}
        for name, value in inspect.getmembers(self, inspect.ismethod):
            if getattr(value, '_jabberbot_command', False):
                name = getattr(value, '_jabberbot_command_name')
                self.log.info('Registered command: %s' % name)
                self.commands[name] = value

    def _send_status(self):
        """Send status to everyone"""
        pres = xmpp.dispatcher.Presence(show=self.__show, status=self.__status)
        pres.setTag('c', namespace=NS_CAPS, attrs=HIPCHAT_PRESENCE_ATTRS)

        self.conn.send(pres)

    def __set_status(self, value):
        """Set status message.
        If value remains constant, no presence stanza will be send"""
        if self.__status != value:
            self.__status = value
            self._send_status()

    def __get_status(self):
        """Get current status message"""
        return self.__status

    status_message = property(fget=__get_status, fset=__set_status)

    def __set_show(self, value):
        """Set show (status type like AWAY, DND etc.).
        If value remains constant, no presence stanza will be send"""
        if self.__show != value:
            self.__show = value
            self._send_status()

    def __get_show(self):
        """Get current show (status type like AWAY, DND etc.)."""
        return self.__show

    status_type = property(fget=__get_show, fset=__set_show)

    ################################

    def connect(self):
        """Connects the bot to server or returns current connection,
        send inital presence stanza
        and registers handlers
        """
        if not self.conn:
            self.log.info('Start Connection ...........')
            #TODO improve debug
            if self.__debug:
                conn = xmpp.Client(self.jid.getDomain())
            else:
                conn = xmpp.Client(self.jid.getDomain(), debug=[])

            conn.UnregisterDisconnectHandler(conn.DisconnectHandler)
            #connection attempt
            self.log.info('Connect attempt')
            conres = conn.connect()
            if not conres:
                self.log.error('unable to connect to server %s.' %
                               self.jid.getDomain())
                return None
            if conres != 'tls':
                self.log.warning('unable to establish secure connection '\
                                 '- TLS failed!')
            self.log.info('Auth attempt')
            authres = conn.auth(self.jid.getNode(), self.__password, self.res)
            if not authres:
                self.log.error('unable to authorize with server.')
                return None
            if authres != 'sasl':
                self.log.warning("unable to perform SASL auth on %s. "\
                                 "Old authentication method used!" % self.jid.getDomain())
            self.log.info('Connection established')
            # Connection established - save connection
            self.conn = conn

            # Send initial presence stanza (say hello to everyone)
            self.log.info('Send Hello to everyone')
            self.conn.sendInitPresence()
            # Save roster and log Items
            self.log.info('Get Roster')
            self.roster = self.conn.Roster.getRoster()
            self.log.info('*** roster ***')
            for contact in self.roster.getItems():
                self.log.info('  %s' % contact)
            self.log.info('*** roster ***')

            # Register given handlers (TODO move to own function)
            for (handler, callback) in self.handlers:
                self.conn.RegisterHandler(handler, callback)
                self.log.info('Registered handler: %s' % handler)
            self.log.info('............ Connection Done')

        return self.conn

    def join_room(self, room, username=None, password=None):
        """Join the specified multi-user chat room

        If username is NOT provided fallback to node part of JID"""
        # TODO fix namespacestrings and history settings
        NS_MUC = 'http://jabber.org/protocol/muc'
        if username is None:
        # TODO use xmpppy function getNode
            username = self.__username.split('@')[0]
        my_room_JID = '/'.join((room, username))
        pres = xmpp.dispatcher.Presence(to=my_room_JID) #, frm=self.__username + '/bot')
        pres.setTag('c', namespace=NS_CAPS, attrs=HIPCHAT_PRESENCE_ATTRS)
        t = pres.setTag('x', namespace=NS_MUC)
        if password is not None:
            t.setTagData('password', password)
        self.log.info(pres)
        self.send_message(pres)

    def kick(self, room, nick, reason=None):
        """Kicks user from muc
        Works only with sufficient rights."""
        NS_MUCADMIN = 'http://jabber.org/protocol/muc#admin'
        item = xmpp.simplexml.Node('item')
        item.setAttr('nick', nick)
        item.setAttr('role', 'none')
        iq = xmpp.Iq(typ='set', queryNS=NS_MUCADMIN, xmlns=None, to=room, payload=item)
        if reason is not None:
            item.setTagData('reason', reason)
            self.connect().send(iq)

    def invite(self, room, jids, reason=None):
        """Invites user to muc.
        Works only if user has permission to invite to muc"""
        NS_MUCUSER = 'http://jabber.org/protocol/muc#user'
        mess = xmpp.Message(to=room)
        for jid in jids:
            invite = xmpp.simplexml.Node('invite')
            invite.setAttr('to', jid)
            if reason is not None:
                invite.setTagData('reason', reason)
            mess.setTag('x', namespace=NS_MUCUSER).addChild(node=invite)
        self.log.info(mess)
        self.connect().send(mess)

    def quit(self, return_code = -1):
        """Stop serving messages and exit.

        I find it is handy for development to run the
        jabberbot in a 'while true' loop in the shell, so
        whenever I make a code change to the bot, I send
        the 'reload' command, which I have mapped to call
        self.quit(), and my shell script relaunches the
        new version.
        """
        self.__finished = True
        self.return_code = return_code

    def send_message(self, mess):
        """Send an XMPP message"""
        self.connect().send(mess)

    def send_tune(self, song, debug=False):
        """Set information about the currently played tune

        Song is a dictionary with keys: file, title, artist, album, pos, track,
        length, uri. For details see <http://xmpp.org/protocols/tune/>.
        """
        NS_TUNE = 'http://jabber.org/protocol/tune'
        iq = xmpp.Iq(typ='set')
        iq.setFrom(self.jid)
        iq.pubsub = iq.addChild('pubsub', namespace=xmpp.NS_PUBSUB)
        iq.pubsub.publish = iq.pubsub.addChild('publish',
            attrs={'node': NS_TUNE})
        iq.pubsub.publish.item = iq.pubsub.publish.addChild('item',
            attrs={'id': 'current'})
        tune = iq.pubsub.publish.item.addChild('tune')
        tune.setNamespace(NS_TUNE)

        title = None
        if song.has_key('title'):
            title = song['title']
        elif song.has_key('file'):
            title = os.path.splitext(os.path.basename(song['file']))[0]
        if title is not None:
            tune.addChild('title').addData(title)
        if song.has_key('artist'):
            tune.addChild('artist').addData(song['artist'])
        if song.has_key('album'):
            tune.addChild('source').addData(song['album'])
        if song.has_key('pos') and song['pos'] > 0:
            tune.addChild('track').addData(str(song['pos']))
        if song.has_key('time'):
            tune.addChild('length').addData(str(song['time']))
        if song.has_key('uri'):
            tune.addChild('uri').addData(song['uri'])

        if debug:
            self.log.info('Sending tune: %s' % iq.__str__().encode('utf8'))
        self.conn.send(iq)

    def send(self, user, text, in_reply_to=None, message_type='chat'):
        """Sends a simple message to the specified user."""
        mess = self.build_message(text)
        mess.setTo(user)

        if in_reply_to:
            mess.setThread(in_reply_to.getThread())
            mess.setType(in_reply_to.getType())
        else:
            mess.setThread(self.__threads.get(user, None))
            mess.setType(message_type)

        self.send_message(mess)

    def send_simple_reply(self, mess, text, private=False):
        """Send a simple response to a message"""
        self.send_message(self.build_reply(mess, text, private))

    def build_reply(self, mess, text=None, private=False):
        """Build a message for responding to another message.
        Message is NOT sent"""
        response = self.build_message(text)
        if private:
            response.setTo(mess.getFrom())
            response.setType('chat')
        else:
            response.setTo(mess.getFrom().getStripped())
            response.setType(mess.getType())
        response.setThread(mess.getThread())
        return response

    def build_message(self, text):
        """Builds an xhtml message without attributes.
        If input is not valid xhtml-im fallback to normal."""
        # Try to determine if text has xhtml-tags - TODO needs improvement
        text_plain = re.sub(r'<br/>', '\n', text)
        text_plain = re.sub(r'&nbsp;', ' ', text_plain)
        text_plain = re.sub(r'<[^>]+>', '', text_plain).strip()
        message = xmpp.protocol.Message(body=text_plain)
        if text_plain != text:
            message.addChild(node = XML2Node(text))
        return message


    def get_full_jids(self, jid):
        """Returns all full jids, which belong to a bare jid

        Example: A bare jid is bob@jabber.org, with two clients connected,
        which
        have the full jids bob@jabber.org/home and bob@jabber.org/work."""
        for res in self.roster.getResources(jid):
            full_jid = "%s/%s" % (jid, res)
            yield full_jid

    def status_type_changed(self, jid, new_status_type):
        """Callback for tracking status types (dnd, away, offline, ...)"""
        self.log.debug('user %s changed status to %s' % (jid, new_status_type))

    def status_message_changed(self, jid, new_status_message):
        """Callback for tracking status messages (the free-form status text)"""
        self.log.debug('user %s updated text to %s' %
                       (jid, new_status_message))

    def broadcast(self, message, only_available=False):
        """Broadcast a message to all users 'seen' by this bot.

        If the parameter 'only_available' is True, the broadcast
        will not go to users whose status is not 'Available'."""
        for jid, (show, status) in self.__seen.items():
            print str(jid) + ' - ' + str(show) + ' - ' + str(status)
            if not only_available or show is self.AVAILABLE:
                self.send(jid, message)
            else:
                print 'not available'

    def callback_presence(self, conn, presence):
        self.__lastping = time.time()
        jid, type_, show, status = presence.getFrom(),\
                                   presence.getType(), presence.getShow(),\
                                   presence.getStatus()

        if self.jid.bareMatch(jid):
            # update internal status
            if type_ != self.OFFLINE:
                self.__status = status
                self.__show = show
            else:
                self.__status = ""
                self.__show = self.OFFLINE
            if not self.__acceptownmsgs:
                # Ignore our own presence messages
                return

        if type_ is None:
            # Keep track of status message and type changes
            old_show, old_status = self.__seen.get(jid, (self.OFFLINE, None))
            if old_show != show:
                self.status_type_changed(jid, show)

            if old_status != status:
                self.status_message_changed(jid, status)

            self.__seen[jid] = (show, status)
        elif type_ == self.OFFLINE and jid in self.__seen:
            # Notify of user offline status change
            del self.__seen[jid]
            self.status_type_changed(jid, self.OFFLINE)

        try:
            subscription = self.roster.getSubscription(unicode(jid.__str__()))
        except KeyError, e:
            # User not on our roster
            subscription = None
        except AttributeError, e:
            # Recieved presence update before roster built
            return

        if type_ == 'error':
            error = presence.getTag('error')
            text = ''
            if error:
                text = error.getTag('text')
                if text:
                    data = text.getData()
                    self.log.error('Presence Error: ' + presence.getError() + ' : ' + data)
                else:
                    self.log.error('Presence Error: %s' % presence)
            else:
                self.log.error('Presence Error: %s' % presence)


        self.log.debug('Got presence: %s (type: %s, show: %s, status: %s, '\
                       'subscription: %s)' % (jid, type_, show, status, subscription))

        # If subscription is private,
        # disregard anything not from the private domain
        if self.__privatedomain and type_ in ('subscribe', 'subscribed', 'unsubscribe'):
            if self.__privatedomain:
                # Use the bot's domain
                domain = self.jid.getDomain()
            else:
                # Use the specified domain
                domain = self.__privatedomain

            # Check if the sender is in the private domain
            user_domain = jid.getDomain()
            if domain != user_domain:
                self.log.info('Ignoring subscribe request: %s does not '\
                              'match private domain (%s)' % (user_domain, domain))
                return

        if type_ == 'subscribe':
            # Incoming presence subscription request
            if subscription in ('to', 'both', 'from'):
                self.roster.Authorize(jid)
                self._send_status()

            if subscription not in ('to', 'both'):
                self.roster.Subscribe(jid)

            if subscription in (None, 'none'):
                self.send(jid, self.MSG_AUTHORIZE_ME)
        elif type_ == 'subscribed':
            # Authorize any pending requests for that JID
            self.roster.Authorize(jid)
        elif type_ == 'unsubscribed':
            # Authorization was not granted
            self.send(jid, self.MSG_NOT_AUTHORIZED)
            self.roster.Unauthorize(jid)

    def callback_message(self, conn, mess):
        """Messages sent to the bot will arrive here.
        Command handling + routing is done in this function."""
        self.__lastping = time.time()

        # Prepare to handle either private chats or group chats
        type = mess.getType()
        jid = mess.getFrom()
        props = mess.getProperties()
        text = mess.getBody()
        username = get_sender_username(mess)

        if type not in ("groupchat", "chat"):
            self.log.debug("unhandled message type %s" % mess)
            return

        if is_from_history(mess):
            self.log.debug("Message from history, ignore it")
            return

        self.log.debug("*** props = %s" % props)
        self.log.debug("*** jid = %s" % jid)
        self.log.debug("*** username = %s" % username)
        self.log.debug("*** type = %s" % type)
        self.log.debug("*** text = %s" % text)

        # If a message format is not supported (eg. encrypted),
        # txt will be None
        if not text: return

        # Remember the last-talked-in message thread for replies
        # FIXME i am not threadsafe
        self.__threads[jid] = mess.getThread()

        if not text.startswith('!'):
            return

        text = text[1:]
        text_split = text.strip().split(' ')

        cmd = None
        command = None
        args = ''
        if len(text_split) > 1:
            command = (text_split[0] + '_' + text_split[1]).lower()
            if self.commands.has_key(command):
                cmd = command
                args = ' '.join(text_split[2:])

        if not cmd:
            command = text_split[0].lower()
            args = ' '.join(text_split[1:])
            if self.commands.has_key(command):
                cmd = command
                if len(text_split) > 1:
                    args = ' '.join(text_split[1:])

        if command == '!': # we did "!!" so recall the last command
            if len(self.cmd_history):
                cmd, args = self.cmd_history[-1]
            else:
                return # no command in history
        elif command.isdigit(): # we did "!#" so we recall the specified command
            index = int(command)
            if len(self.cmd_history) >= index:
                cmd, args = self.cmd_history[-index]
            else:
                return # no command in history

        if (cmd, args) in self.cmd_history:
            self.cmd_history.remove((cmd, args)) # we readd it below

        self.log.info("received command = %s matching [%s] with parameters [%s]" % (command, cmd, args))

        if cmd:
            def execute_and_send(template_name):
                try:
                    reply = self.commands[cmd](mess, args)

                    # integrated templating
                    if template_name:
                        reply = tenv.get_template(template_name + '.html').render(**reply)

                except Exception, e:
                    self.log.exception('An error happened while processing '\
                                       'a message ("%s") from %s: %s"' %
                                       (text, jid, traceback.format_exc(e)))
                    reply = self.MSG_ERROR_OCCURRED + ':\n %s' % e
                if reply:
                    if len(reply) > self.MESSAGE_SIZE_LIMIT:
                        reply = reply[:self.MESSAGE_SIZE_LIMIT - len(self.MESSAGE_SIZE_ERROR_MESSAGE)] + self.MESSAGE_SIZE_ERROR_MESSAGE
                    self.send_simple_reply(mess, reply)

            f = self.commands[cmd]

            if f._jabberbot_command_admin_only:
                if mess.getType() == 'groupchat':
                    self.send_simple_reply(mess, 'You cannot administer the bot from a chatroom, message the bot directly')
                    return
                usr = get_jid_from_message(mess)
                if usr not in BOT_ADMINS:
                    self.send_simple_reply(mess, 'You cannot administer the bot from this user %s.' % usr)
                    return

            if f._jabberbot_command_historize:
                self.cmd_history.append((cmd,  args)) # add it to the history only if it is authorized to be so

            if f._jabberbot_command_split_args_with:
                args = args.split(f._jabberbot_command_split_args_with)

            # Experimental!
            # if command should be executed in a seperate thread do it
            if f._jabberbot_command_thread:
                thread.start_new_thread(execute_and_send, (f._jabberbot_command_template,))
            else:
                execute_and_send(f._jabberbot_command_template)
        else:
            # In private chat, it's okay for the bot to always respond.
            # In group chat, the bot should silently ignore commands it
            # doesn't understand or aren't handled by unknown_command().
            reply = self.unknown_command(mess, command, args)
            if reply is None:
                reply = self.MSG_UNKNOWN_COMMAND % {'command': command}
            if reply:
                self.send_simple_reply(mess, reply)

    def unknown_command(self, mess, cmd, args):
        """Default handler for unknown commands

        Override this method in derived class if you
        want to trap some unrecognized commands.  If
        'cmd' is handled, you must return some non-false
        value, else some helpful text will be sent back
        to the sender.
        """
        return None

    def top_of_help_message(self):
        """Returns a string that forms the top of the help message

        Override this method in derived class if you
        want to add additional help text at the
        beginning of the help message.
        """
        return ""

    def bottom_of_help_message(self):
        """Returns a string that forms the bottom of the help message

        Override this method in derived class if you
        want to add additional help text at the end
        of the help message.
        """
        return ""

    @botcmd
    def help(self, mess, args):
        """   Returns a help string listing available options.

        Automatically assigned to the "help" command."""
        if not args:
            if self.__doc__:
                description = self.__doc__.strip()
            else:
                description = 'Available commands:'

            usage = '\n'.join(sorted([
            '!%s: %s' % (name, (command.__doc__ or
                                '(undocumented)').strip().split('\n', 1)[0])
            for (name, command) in self.commands.iteritems()\
            if name != 'help'\
            and not command._jabberbot_command_hidden
            ]))
            usage = '\n\n' + '\n\n'.join(filter(None, [usage, self.MSG_HELP_TAIL]))
        else:
            description = ''
            if args in self.commands:
                usage = (self.commands[args].__doc__ or
                         'undocumented').strip()
            else:
                usage = self.MSG_HELP_UNDEFINED_COMMAND

        top = self.top_of_help_message()
        bottom = self.bottom_of_help_message()
        return ''.join(filter(None, [top, description, usage, bottom]))

    def idle_proc(self):
        """This function will be called in the main loop."""
        self._idle_ping()

    def _idle_ping(self):
        """Pings the server, calls on_ping_timeout() on no response.

        To enable set self.PING_FREQUENCY to a value higher than zero.
        """
        if self.PING_FREQUENCY and time.time() - self.__lastping > self.PING_FREQUENCY:
            self.__lastping = time.time()
            #logging.debug('Pinging the server.')
            ping = xmpp.Protocol('iq', typ='get',
                payload=[xmpp.Node('ping', attrs={'xmlns': 'urn:xmpp:ping'})])
            try:
                if self.conn:
#Traceback (most recent call last):
#    File "dockstar-gtalk.py", line 142, in <module>
#        main()
#      File "dockstar-gtalk.py", line 93, in main
#        holder.bot.serve_forever()
#      File "/opt/dockstarmailer/dockstar-gtalk/err/errbot/jabberbot.py", line 802, in serve_forever
#        self.idle_proc()
#      File "/opt/dockstarmailer/dockstar-gtalk/err/errbot/jabberbot.py", line 748, in idle_proc
#        self._idle_ping()
#      File "/opt/dockstarmailer/dockstar-gtalk/err/errbot/jabberbot.py", line 762, in _idle_ping
#        res = self.conn.SendAndWaitForResponse(ping, self.PING_TIMEOUT)
#      File "/opt/dockstarmailer/dockstar-gtalk/xmpp/dispatcher.py", line 337, in
#  SendAndWaitForResponse
#        return self.WaitForResponse(self.send(stanza),timeout)
#      File "/opt/dockstarmailer/dockstar-gtalk/xmpp/dispatcher.py", line 321, in WaitForResponse
#        if not self.Process(0.04):
#            File "/opt/dockstarmailer/dockstar-gtalk/xmpp/dispatcher.py", line 122, in Process
#                self.Stream.Parse(data)
#            xml.parsers.expat.ExpatError: mismatched tag: line 1, column 971
#
# Got above, hence changed IOError to Exception for futher investigation. Lets see if the domain
# persists
                    res = self.conn.SendAndWaitForResponse(ping, self.PING_TIMEOUT)
                    logging.debug('Got response: ' + str(res))
                    if res is None:
                        self.on_ping_timeout()
                else:
                    logging.debug('Ping cancelled : No connectivity.')
            except Exception, e:
                logging.error('Error pinging the server: %s, '\
                              'treating as ping timeout.' % e)
                self.on_ping_timeout()

    def on_ping_timeout(self):
        logging.warning('Connection ping timeoutted, closing connection')
        self.conn = None

    def shutdown(self):
        """This function will be called when we're done serving

        Override this method in derived class if you
        want to do anything special at shutdown.
        """
        pass

    def serve_forever(self, connect_callback=None, disconnect_callback=None):
        """Connects to the server and handles messages."""
        conn = None
        while not self.__finished and not conn:
            conn = self.connect()
            if not conn:
                self.log.warn('could not connect to server - sleeping %i seconds.' % self.RETRY_FREQUENCY)
                time.sleep(self.RETRY_FREQUENCY)

        if connect_callback:
            connect_callback()
        self.__lastping = time.time()

        while not self.__finished:
            try:
                if conn:
                    conn.Process(1)
                    self.idle_proc()
                else:
                    self.log.warn('Connection lost, retry to connect in %i seconds.' % self.RETRY_FREQUENCY)
                    time.sleep(self.RETRY_FREQUENCY)
                    conn = self.connect()
            except KeyboardInterrupt:
                self.log.info('bot stopped by user request. shutting down.')
                break

        if disconnect_callback:
            disconnect_callback()
        self.shutdown()
        exit(self.return_code)

# vim: expandtab tabstop=4 shiftwidth=4 softtabstop=4
