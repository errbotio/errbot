import logging
import re
import sys
from functools import lru_cache

from errbot.backends.base import Room, RoomDoesNotExistError, RoomOccupant, Stream
from errbot.backends.xmpp import XMPPRoomOccupant, XMPPBackend, XMPPConnection, split_identifier

from markdown import Markdown
from markdown.extensions.extra import ExtraExtension
from markdown.extensions import Extension
from markdown.treeprocessors import Treeprocessor

from email.mime.multipart import MIMEMultipart
import email.mime.application

import requests

log = logging.getLogger(__name__)

try:
    import hypchat
except ImportError:
    log.exception("Could not start the HipChat backend")
    log.fatal(
        "You need to install the hipchat support in order to use the HipChat backend.\n "
        "You should be able to install this package using:\n"
        "pip install errbot[hipchat]"
    )
    sys.exit(1)

COLORS = {
    'blue': 'purple',
    'white': 'gray',
    'black': 'gray',
}  # best effort to map errbot colors to hipchat ones,


# Rendering customizations
class HipchatTreeprocessor(Treeprocessor):
    def run(self, root):
        def recurse_patch(element):
            t = element.tag
            if t == 'h1':
                element.tag = 'strong'
                element.text = element.text.upper()
            elif t == 'h2':
                element.tag = 'em'
            elif t in ('h3', 'h4', 'h5', 'h6'):
                element.tag = 'p'
            elif t == 'hr':
                element.tag = 'p'
                element.text = '─' * 80

            for elems in element:
                recurse_patch(elems)
        recurse_patch(root)


class HipchatExtension(Extension):
    """Removes the unsupported html tags from hipchat"""

    def extendMarkdown(self, md, md_globals):
        md.registerExtension(self)
        md.treeprocessors.add("hipchat stripper", HipchatTreeprocessor(), '<inline')
        log.debug("Will apply those treeprocessors:\n%s", md.treeprocessors)


def hipchat_html():
    return Markdown(output_format='xhtml', extensions=[ExtraExtension(), HipchatExtension()])


class HipChatRoomOccupant(XMPPRoomOccupant):
    """
    An occupant of a Multi-User Chatroom.

    This class has all the attributes that are returned by a call to
    https://www.hipchat.com/docs/apiv2/method/get_all_participants
    with the link to self expanded.
    """
    def __init__(self, node=None, domain=None, resource=None, room=None, hipchat_user=None, aclattr=None):
        """
        :param hipchat_user:
            A user object as returned by
            https://www.hipchat.com/docs/apiv2/method/get_all_participants
            with the link to self expanded.
        """
        if hipchat_user:
            for k, v in hipchat_user.items():
                setattr(self, k, v)
            # Quick fix to be able to all the parent.
            if '/' in hipchat_user['xmpp_jid']:
                node_domain, resource = hipchat_user['xmpp_jid'].split('/')
            else:
                node_domain = hipchat_user['xmpp_jid']
                resource = hipchat_user['name']
            node, domain = node_domain.split('@')

        self._aclattr = aclattr

        super().__init__(node, domain, resource, room)

    @property
    def aclattr(self):
        return self._aclattr


class HipChatRoom(Room):
    """
    This class represents a Multi-User Chatroom.
    """

    def __init__(self, name, bot):
        """
        :param name:
            The name of the room
        """
        self.name = name
        self.hypchat = bot.conn.hypchat
        self.xep0045 = bot.conn.client.plugin['xep_0045']
        self._bot = bot

    @property
    def room(self):
        """
        Return room information from the HipChat API
        """
        try:
            log.debug('Querying HipChat API for room %s.', self.name)
            return self.hypchat.get_room(self.name)
        except hypchat.requests.HttpNotFound:
            raise RoomDoesNotExistError('The given room does not exist.')

    @property
    def name(self):
        """
        The name of this room
        """
        return self._name

    @name.setter
    def name(self, name):
        self._name = name

    @property
    def jid(self):
        return self.room['xmpp_jid']

    @property
    def node(self):
        return self._bot.build_identifier(self.jid).node

    @property
    def domain(self):
        return self._bot.build_identifier(self.jid).domain

    @property
    def resource(self):
        return self._bot.build_identifier(self.jid).resource

    def __repr__(self):
        return f"<HipChatMUCRoom('{self.name}')>"

    def __str__(self):
        return self.room['xmpp_jid']

    def join(self, username=None, password=None):
        """
        Join the room.

        If the room does not exist yet, this will automatically call
        :meth:`create` on it first.
        """
        if not self.exists:
            self.create()

        room = self.jid
        self.xep0045.joinMUC(room, username, password=password, wait=True)
        self._bot.conn.add_event_handler(f'muc::{room}::got_online', self._bot.user_joined_chat)
        self._bot.conn.add_event_handler(f'muc::{room}::got_offline', self._bot.user_left_chat)

        self._bot.callback_room_joined(self)
        log.info('Joined room %s.', self.name)

    def leave(self, reason=None):
        """
        Leave the room.

        :param reason:
            An optional string explaining the reason for leaving the room
        """
        if reason is None:
            reason = ""
        room = self.jid
        try:
            self.xep0045.leaveMUC(room=room, nick=self.xep0045.ourNicks[room], msg=reason)
            self._bot.conn.del_event_handler(f'muc::{room}::got_online', self._bot.user_joined_chat)
            self._bot.conn.del_event_handler(f'muc::{room}::got_offline', self._bot.user_left_chat)
            log.info('Left room %s', self)
            self._bot.callback_room_left(self)
        except KeyError:
            log.debug('Trying to leave %s while not in this room.', self)

    def create(self, privacy='public', guest_access=False):
        """
        Create the room.

        Calling this on an already existing room is a no-op.

        :param privacy:
            Whether the room is available for access by other users or not.
            Valid values are "public" and "private".
        :param guest_access:
            Whether or not to enable guest access for this room.
        """
        if self.exists:
            log.debug('Tried to create the room %s, but it has already been created', self)
        else:
            self.hypchat.create_room(
                name=self.name,
                privacy=privacy,
                guest_access=guest_access
            )
            log.info('Created room %s.', self)

    def destroy(self):
        """
        Destroy the room.

        Calling this on a non-existing room is a no-op.
        """
        try:
            self.room.delete()
            log.info('Destroyed room %s.', self)
        except RoomDoesNotExistError:
            log.debug("Can't destroy room %s, it doesn't exist.", self)

    @property
    def exists(self):
        """
        Boolean indicating whether this room already exists or not.

        :getter:
            Returns `True` if the room exists, `False` otherwise.
        """
        try:
            self.hypchat.get_room(self.name)
            return True
        except hypchat.requests.HttpNotFound:
            return False

    @property
    def joined(self):
        """
        Boolean indicating whether this room has already been joined or not.

        :getter:
            Returns `True` if the room has been joined, `False` otherwise.
        """
        return self.jid in self.xep0045.getJoinedRooms()

    @property
    def topic(self):
        """
        The room topic.

        :getter:
            Returns the topic (a string) if one is set, `None` if no
            topic has been set at all.
        """
        return self.room['topic']

    @topic.setter
    def topic(self, topic):
        """
        Set the room's topic.

        :param topic:
            The topic to set.
        """
        self.room.topic(topic)
        log.debug('Changed topic of %s to %s', self, topic)

    @property
    def occupants(self):
        """
        The room's occupants.

        :getter:
            Returns a list of :class:`~HipChatMUCOccupant` instances.
        """
        participants = self.room.participants(expand='items')['items']
        occupants = []
        for p in participants:
            occupants.append(HipChatRoomOccupant(hipchat_user=p))
        return occupants

    def invite(self, *args):
        """
        Invite one or more people into the room.

        :param args:
            One or more people to invite into the room. May be the
            mention name (beginning with an @) or "FirstName LastName"
            of the user you wish to invite.
        """
        room = self.room
        users = self._bot.conn.users

        for person in args:
            try:
                if person.startswith('@'):
                    user = [u for u in users if u['mention_name'] == person[1:]][0]
                else:
                    user = [u for u in users if u['name'] == person][0]
            except IndexError:
                logging.warning('No user by the name of %s found.', person)
            else:
                if room['privacy'] == 'private':
                    room.members().add(user)
                    log.info('Added %s to private room %s.', user['name'], self)
                room.invite(user, 'No reason given.')
                log.info('Invited %s to %s.', person, self)

    def notify(self, message, color=None, notify=False, message_format=None):
        """
        Send a notification to a room.

        See the
        `HipChat API documentation <https://www.hipchat.com/docs/apiv2/method/send_room_notification>`_
        for more info.
        """
        self.room.notification(message=message, color=color, notify=notify, format=message_format)


class HipchatClient(XMPPConnection):
    def __init__(self, *args, **kwargs):
        self.token = kwargs.pop('token')
        self.endpoint = kwargs.pop('endpoint')
        self._cached_users = None
        verify = kwargs.pop('verify')
        if verify is None:
            verify = True
        if self.endpoint is None:
            self.hypchat = hypchat.HypChat(self.token, verify=verify)
        else:
            # We could always pass in the endpoint, with a default value if it's
            # None, but this way we support hypchat<0.18
            self.hypchat = hypchat.HypChat(self.token, endpoint=self.endpoint, verify=verify)
        super().__init__(*args, **kwargs)

    @property
    def users(self):
        """
        A list of all the users.

        See also: https://www.hipchat.com/docs/apiv2/method/get_all_users
        """

        if not self._cached_users:
            result = self.hypchat.users(guests=True)
            users = result['items']
            next_link = 'next' in result['links']
            while next_link:
                result = result.next()
                users += result['items']
                next_link = 'next' in result['links']
            self._cached_users = users
        return self._cached_users


class HipchatBackend(XMPPBackend):
    room_factory = HipChatRoom
    roomoccupant_factory = HipChatRoomOccupant

    def __init__(self, config):
        self.api_token = config.BOT_IDENTITY['token']
        self.api_endpoint = config.BOT_IDENTITY.get('endpoint', None)
        self.api_verify = config.BOT_IDENTITY.get('verify', True)
        self.md = hipchat_html()
        super().__init__(config)

    def create_connection(self):
        # HipChat connections time out with the default keepalive interval
        # so use a lower value that is known to work, but only if the user
        # does not specify their own value in their config.
        if self.keepalive is None:
            self.keepalive = 60

        return HipchatClient(
            jid=self.jid,
            password=self.password,
            feature=self.feature,
            keepalive=self.keepalive,
            ca_cert=self.ca_cert,
            token=self.api_token,
            endpoint=self.api_endpoint,
            server=self.server,
            verify=self.api_verify,
        )

    def _build_room_occupant(self, txtrep):
        node, domain, resource = split_identifier(txtrep)
        return self.roomoccupant_factory(node,
                                         domain,
                                         resource,
                                         self.query_room(node + '@' + domain),
                                         aclattr=self._find_user(resource, 'name'))

    def callback_message(self, msg):
        super().callback_message(msg)
        possible_mentions = re.findall(r'@\w+', msg.body)
        people = list(
            filter(None.__ne__, [self._find_user(mention[1:], 'mention_name') for mention in possible_mentions])
        )

        if people:
            self.callback_mention(msg, people)

    @property
    def mode(self):
        return 'hipchat'

    def rooms(self):
        """
        Return a list of rooms the bot is currently in.

        :returns:
            A list of :class:`~HipChatRoom` instances.
        """
        xep0045 = self.conn.client.plugin['xep_0045']
        rooms = {}
        # Build a mapping of xmpp_jid->name for easy reference
        for room in self.conn.hypchat.rooms(expand='items').contents():
            rooms[room['xmpp_jid']] = room['name']

        joined_rooms = []
        for room in xep0045.getJoinedRooms():
            try:
                joined_rooms.append(HipChatRoom(rooms[room], self))
            except KeyError:
                pass
        return joined_rooms

    @lru_cache(1024)
    def query_room(self, room):
        """
        Query a room for information.

        :param room:
            The name (preferred) or XMPP JID of the room to query for.
        :returns:
            An instance of :class:`~HipChatRoom`.
        """
        if room.endswith('@conf.hipchat.com') or room.endswith('@conf.btf.hipchat.com'):
            log.debug("Room specified by JID, looking up room name")
            rooms = self.conn.hypchat.rooms(expand='items').contents()
            try:
                name = [r['name'] for r in rooms if r['xmpp_jid'] == room][0]
            except IndexError:
                raise RoomDoesNotExistError(f'No room with JID {room} found.')
            log.info('Found %s to be the room %s, consider specifying this directly.', room, name)
        else:
            name = room

        return HipChatRoom(name, self)

    def build_reply(self, msg, text=None, private=False, threaded=False):
        response = super().build_reply(msg=msg, text=text, private=private, threaded=threaded)
        if msg.is_group and msg.frm == response.to:
            # HipChat violates the XMPP spec :( This results in a valid XMPP JID
            # but HipChat mangles them into stuff like
            # "132302_961351@chat.hipchat.com/none||proxy|pubproxy-b100.hipchat.com|5292"
            # so we request the user's proper JID through their API and use that here
            # so that private responses originating from a room (IE, DIVERT_TO_PRIVATE)
            # work correctly.
            response.to = self._find_user(response.to.client, 'name')
        return response

    def send_card(self, card):
        if isinstance(card.to, RoomOccupant):
            card.to = card.to.room
        if not card.is_group:
            raise ValueError('Private notifications/cards are impossible to send on 1 to 1 messages on hipchat.')
        log.debug('room id = %s', card.to)
        room = self.query_room(str(card.to)).room

        data = {'message': '-' if not card.body else self.md.convert(card.body),
                'notify': False,
                'message_format': 'html'}

        if card.color:
            data['color'] = COLORS[card.color] if card.color in COLORS else card.color

        hcard = {'id': f'FF{card.__hash__():0.16X}'}

        # Only title is supported all across the types.
        if card.title:
            hcard['title'] = card.title
        else:
            hcard['title'] = ' '  # title is mandatory, more that 1 chr.

        # Go from the most restrictive type to the less resctrictive to find the most appropriate.
        if card.image and not card.summary and not card.fields and not card.link:
            hcard['style'] = 'image'
            hcard['thumbnail'] = {'url': card.image if not card.thumbnail else card.thumbnail}
            hcard['url'] = card.image
            if card.body:
                data['message'] = card.body  # We don't have a card body field so retrofit it to the main body.
        elif card.link and not card.summary and not card.fields:
            hcard['style'] = 'link'
            hcard['url'] = card.link
            if card.thumbnail:
                hcard['icon'] = {'url': card.thumbnail}
            if card.image:
                hcard['thumbnail'] = {'url': card.image}
            if card.body:
                hcard['description'] = card.body
        else:
            hcard['style'] = 'application'
            hcard['format'] = 'medium'
            if card.image and card.thumbnail:
                log.warning('Hipchat cannot display this card with an image.'
                            'Remove summary, fields and/or possibly link to fallback to an hichat link or '
                            'an image style card.')
            if card.image or card.thumbnail:
                hcard['icon'] = {'url': card.thumbnail if card.thumbnail else card.image}
            if card.body:
                hcard['description'] = card.body
            if card.summary:
                hcard['activity'] = {'html': card.summary}
            if card.fields:
                hcard['attributes'] = [{'label': key, 'value': {'label': value, 'style': 'lozenge-complete'}}
                                       for key, value in card.fields]
            if card.link:
                hcard['url'] = card.link

        data['card'] = hcard

        log.debug("Sending request:" + str(data))
        room._requests.post(room.url + '/notification', data=data)  # noqa

    def send_stream_request(self, identifier, fsource, name='file.txt', size=None, stream_type=None):
        """Starts a file transfer.
            note, fsource used to make the stream needs to be in open/rb state
        """

        stream = Stream(identifier=identifier, fsource=fsource, name=name, size=size, stream_type=stream_type)
        result = self.thread_pool.apply_async(self._hipchat_upload, (stream,))
        log.debug('Response from server: %s', result.get(timeout=10))
        return stream

    def _hipchat_upload(self, stream):
        """ Uploads file in a stream  """
        try:
            stream.accept()
            room = self.query_room(str(stream.identifier)).room
            headers = {
                'Authorization': f'Bearer {self.api_token}',
                'Accept-Charset': 'UTF-8',
                'Content-Type': 'multipart/related',
            }
            raw_body = MIMEMultipart('related')
            img = email.mime.application.MIMEApplication(stream.read())
            img.add_header(
                'Content-Disposition',
                'attachment',
                name='file',
                filename=stream.name
            )
            raw_body.attach(img)
            raw_headers, body = raw_body.as_string().split('\n\n', 1)
            boundary = re.search('boundary="([^\"]*)"', raw_headers).group(1)
            headers['Content-Type'] = f'multipart/related; boundary="{boundary}"'
            resp = requests.post(room.url + '/share/file', headers=headers, data=body)
            log.info('Request ok: %s.', resp.ok)

            if resp.ok:
                log.info('Request status: %s.', resp.status_code)
                stream.success()
            else:
                log.error('Request status: %s.', resp.status_code)
                log.error('Request reason: %s.', resp.reason)
                log.error('Request text: %s.', resp.text)
                stream.error()
        except Exception:
            log.exception(f'Upload of {stream.name} to {stream.identifier.channelname} failed.')

    @lru_cache(1024)
    def _find_user(self, name, criteria):
        """
        Find a specific hipchat user with a simple criteria like 'name' or 'mention_name' and returns
        its jid.

        :param name: the value you seek.
        :param criteria: 'name' or 'mention_name'
        :return: the matching XMPPPerson or None if not found.
        """
        users = [u for u in self.conn.users if u[criteria] == name]
        if not users:
            log.debug('Failed to find user %s', name)
            return None
        userdetail = self.conn.hypchat.get_user(users[0]['id'])
        identifier = self.build_identifier(userdetail['xmpp_jid'])

        return identifier

    def prefix_groupchat_reply(self, message, identifier):
        message.body = f'@{identifier.nick}: {message.body}'

    def __hash__(self):
        return 0  # it is a singleton anyway
