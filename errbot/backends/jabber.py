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
from pyexpat import ExpatError
from xmpp import Client, NS_DELAY, JID, dispatcher, simplexml, Protocol, Node
from xmpp.client import DBG_CLIENT
from xmpp.protocol import NS_CAPS, Iq, Message, NS_PUBSUB
from xmpp.simplexml import XML2Node
from errbot.backends.base import Connection
from errbot.errBot import ErrBot

from errbot.utils import get_jid_from_message, xhtml2txt


import time
import logging

HIPCHAT_PRESENCE_ATTRS = {'node': 'http://hipchat.com/client/bot', 'ver': 'v1.1.0'}

# need to override it because the send method is created autonagically and I need to override it in certain cases
class JabberClient(Client, Connection):
    def __init__(self, *args, **kwargs):
        self.Namespace,self.DBG='jabber:client',DBG_CLIENT # DAAAAAAAAAAH -> see the CommonClient class, it introspects it descendents to determine that
        super(JabberClient,self).__init__(*args, **kwargs)

    def send_message(self, mess):
        logging.debug('Message filtered thru JabberClient : %s' % mess)
        super(JabberClient,self).send(mess)


def is_from_history(mess):
    props = mess.getProperties()
    return 'urn:xmpp:delay' in props or NS_DELAY in props

class JabberBot(ErrBot):
    # Show types for presence
    AVAILABLE, AWAY, CHAT = None, 'away', 'chat'
    DND, XA, OFFLINE = 'dnd', 'xa', 'unavailable'

    # UI-messages (overwrite to change content)
    MSG_AUTHORIZE_ME = 'Hey there. You are not yet on my roster. '\
                       'Authorize my request and I will do the same.'
    MSG_NOT_AUTHORIZED = 'You did not authorize my subscription request. '\
                         'Access denied.'

    PING_FREQUENCY = 10 # Set to the number of seconds, e.g. 60.
    PING_TIMEOUT = 2 # Seconds to wait for a response.
    RETRY_FREQUENCY = 10 # Set to the number of seconds to attempt another connection attempt in case of connectivity loss

    return_code = 0 # code for the process exit

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
        self.__debug = debug
        self.log = logging.getLogger(__name__)
        self.__username = username
        self.__password = password
        self.jid = JID(self.__username)
        self.res = (res or self.__class__.__name__)
        self.conn = None
        self.__finished = False
        self.__show = None
        self.__status = None
        self.__seen = {}
        self.__lastping = time.time()
        self.__privatedomain = privatedomain
        self.__acceptownmsgs = acceptownmsgs

        self.handlers = (handlers or [('message', self.callback_message),
            ('presence', self.callback_presence)])

        # Collect commands from source
        self.roster = None
        super(JabberBot, self).__init__(username, password, res=res, debug=debug,
                         privatedomain=privatedomain, acceptownmsgs=acceptownmsgs, handlers=handlers)

    ################################

    def _send_status(self):
        """Send status to everyone"""
        pres = dispatcher.Presence(show=self.__show, status=self.__status)
        pres.setTag('c', namespace=NS_CAPS, attrs=HIPCHAT_PRESENCE_ATTRS)

        self.conn.send_message(pres)

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

    # meant to be overridden by XMPP backends variations
    def create_connection(self):
        if self.__debug:
            return JabberClient(self.jid.getDomain())
        return JabberClient(self.jid.getDomain(), debug=[])


    def connect(self):
        """Connects the bot to server or returns current connection,
        send inital presence stanza
        and registers handlers
        """
        if not self.conn:
            self.log.info('Start Connection ...........')
            conn = self.create_connection()
            conn.UnregisterDisconnectHandler(conn.DisconnectHandler)
            #connection attempt
            self.log.info('Connect attempt')
            conres = conn.connect()
            if not conres:
                self.log.error('unable to connect to server %s.' %
                               self.jid.getDomain())
                return None
            if conres != 'tls':
                self.log.warning('unable to establish secure connection - TLS failed!')
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

            # Register given handlers
            for (handler, callback) in self.handlers:
                self.conn.RegisterHandler(handler, callback)
                self.log.info('Registered handler: %s' % handler)
            self.log.info('............ Connection Done')

        return self.conn

    def join_room(self, room, username=None, password=None):
        """Join the specified multi-user chat room

        If username is NOT provided fallback to node part of JID"""
        NS_MUC = 'http://jabber.org/protocol/muc'
        if username is None:
            username = self.__username.split('@')[0]
        my_room_JID = '/'.join((room, username))
        pres = dispatcher.Presence(to=my_room_JID) #, frm=self.__username + '/bot')
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
        item = simplexml.Node('item')
        item.setAttr('nick', nick)
        item.setAttr('role', 'none')
        iq = Iq(typ='set', queryNS=NS_MUCADMIN, xmlns=None, to=room, payload=item)
        if reason is not None:
            item.setTagData('reason', reason)
            self.connect().send(iq)

    def invite(self, room, jids, reason=None):
        """Invites user to muc.
        Works only if user has permission to invite to muc"""
        NS_MUCUSER = 'http://jabber.org/protocol/muc#user'
        mess = Message(to=room)
        for jid in jids:
            invite = simplexml.Node('invite')
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

    def send_tune(self, song, debug=False):
        """Set information about the currently played tune

        Song is a dictionary with keys: file, title, artist, album, pos, track,
        length, uri. For details see <http://xmpp.org/protocols/tune/>.
        """
        NS_TUNE = 'http://jabber.org/protocol/tune'
        iq = Iq(typ='set')
        iq.setFrom(self.jid)
        iq.pubsub = iq.addChild('pubsub', namespace=NS_PUBSUB)
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
        self.conn.send_message(iq)

    def build_message(self, text):
        """Builds an xhtml message without attributes.
        If input is not valid xhtml-im fallback to normal."""
        try:
            node = XML2Node(text)
            # logging.debug('This message is XML : %s' % text)
            text_plain = xhtml2txt(text)
            logging.debug('Plain Text translation from XHTML-IM:\n%s' % text_plain)
            message = Message(body=text_plain)
            message.addChild(node = node)
        except ExpatError as ee:
            if text.strip(): # avoids keep alive pollution
                logging.debug('Could not parse [%s] as XHTML-IM, assume pure text Parsing error = [%s]' % (text, ee))
            message = Message(body=text)
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
        Command handling + routing is done in this function.
        return False if the message should be ignored """
        self.__lastping = time.time()
        if is_from_history(mess):
            self.log.debug("Message from history, ignore it")
            return False

        # Ignore messages from myself
        if self.jid.bareMatch(get_jid_from_message(mess)):
            logging.debug('Ignore a message from myself')
            return False

        return super(JabberBot, self).callback_message(conn, mess)


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
            ping = Protocol('iq', typ='get',
                payload=[Node('ping', attrs={'xmlns': 'urn:xmpp:ping'})])
            try:
                if self.conn:
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

    def serve_forever(self):
        """Connects to the server and handles messages."""
        conn = None
        while not self.__finished and not conn:
            conn = self.connect()
            if not conn:
                self.log.warn('could not connect to server - sleeping %i seconds.' % self.RETRY_FREQUENCY)
                time.sleep(self.RETRY_FREQUENCY)


        self.connect_callback() # notify that the connection occured
        self.__lastping = time.time()

        while not self.__finished:
            try:
                if conn:
                    try:
                        conn.Process(1)
                        if conn._owner.connected == '':
                            self.disconnect_callback() # notify that the connection is lost
                            conn = None
                    except Exception:
                        logging.exception("conn.Process exception")
                    self.idle_proc()
                else:
                    self.log.warn('Connection lost, retry to connect in %i seconds.' % self.RETRY_FREQUENCY)
                    time.sleep(self.RETRY_FREQUENCY)
                    conn = self.connect()
                    if conn:
                        self.connect_callback()
            except KeyboardInterrupt:
                self.log.info('bot stopped by user request. shutting down.')
                break

        self.disconnect_callback()
        self.shutdown()
        exit(self.return_code)

    @property
    def mode(self):
        return 'jabber'

# vim: expandtab tabstop=4 shiftwidth=4 softtabstop=4
