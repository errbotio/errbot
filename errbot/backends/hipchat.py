# -*- coding: utf-8 -*-
# vim: ts=4:sw=4
import logging
import sys

from markdown import Markdown
from markdown.extensions.extra import ExtraExtension
from markdown.extensions import Extension
from markdown.treeprocessors import Treeprocessor

from errbot.backends.base import RoomDoesNotExistError
from errbot.backends.xmpp import XMPPRoomOccupant, XMPPRoom, XMPPBackend, XMPPConnection


# Can't use __name__ because of Yapsy
log = logging.getLogger('errbot.backends.hipchat')

try:
    import hypchat
except ImportError:
    log.exception("Could not start the HipChat backend")
    log.fatal(
        "You need to install the hypchat package in order to use the HipChat "
        "back-end. You should be able to install this package using: "
        "pip install hypchat"
    )
    sys.exit(1)


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
        log.debug("Will apply those treeprocessors:\n%s" % md.treeprocessors)


def hipchat_html():
    return Markdown(output_format='xhtml', extensions=[ExtraExtension(), HipchatExtension()])


class HipChatMUCRoomOccupant(XMPPRoomOccupant):
    """
    An occupant of a Multi-User Chatroom.

    This class has all the attributes that are returned by a call to
    https://www.hipchat.com/docs/apiv2/method/get_all_participants
    with the link to self expanded.
    """
    def __init__(self, user):
        """
        :param user:
            A user object as returned by
            https://www.hipchat.com/docs/apiv2/method/get_all_participants
            with the link to self expanded.
        """
        for k, v in user.items():
            setattr(self, k, v)
        # Quick fix to be able to all the parent.
        node_domain, resource = user['xmpp_jid'].split('/')
        node, domain = node_domain.split('@')
        super().__init__(node, domain, resource)

    def __str__(self):
        return self.name


class HipChatMUCRoom(XMPPRoom):
    """
    This class represents a Multi-User Chatroom.
    """

    def __init__(self, name, bot):
        """
            :param name:
                The name of the room
            """
        super().__init__(name, bot)
        self.hypchat = bot.conn.hypchat

    @property
    def room(self):
        """
        Return room information from the HipChat API
        """
        try:
            log.debug("Querying HipChat API for room {}".format(self.name))
            return self.hypchat.get_room(self.name)
        except hypchat.requests.HttpNotFound:
            raise RoomDoesNotExistError("The given room does not exist.")

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
        return "<HipChatMUCRoom('{}')>".format(self.name)

    def __str__(self):
        return self._name

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
        self._bot.conn.add_event_handler(
            "muc::{}::got_online".format(room),
            self._bot.user_joined_chat
        )
        self._bot.conn.add_event_handler(
            "muc::{}::got_offline".format(room),
            self._bot.user_left_chat
        )

        self._bot.callback_room_joined(self)
        log.info("Joined room {}".format(self.name))

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
            self._bot.conn.del_event_handler(
                "muc::{}::got_online".format(room),
                self._bot.user_joined_chat
            )
            self._bot.conn.del_event_handler(
                "muc::{}::got_offline".format(room),
                self._bot.user_left_chat
            )
            log.info("Left room {}".format(self))
            self._bot.callback_room_left(self)
        except KeyError:
            log.debug("Trying to leave {} while not in this room".format(self))

    def create(self, privacy="public", guest_access=False):
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
            log.debug("Tried to create the room {}, but it has already been created".format(self))
        else:
            self.hypchat.create_room(
                name=self.name,
                privacy=privacy,
                guest_access=guest_access
            )
            log.info("Created room {}".format(self))

    def destroy(self):
        """
        Destroy the room.

        Calling this on a non-existing room is a no-op.
        """
        try:
            self.room.delete()
            log.info("Destroyed room {}".format(self))
        except RoomDoesNotExistError:
            log.debug("Can't destroy room {}, it doesn't exist".format(self))

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
        log.debug("Changed topic of {} to {}".format(self, topic))

    @property
    def occupants(self):
        """
        The room's occupants.

        :getter:
            Returns a list of :class:`~HipChatMUCOccupant` instances.
        """
        participants = self.room.participants(expand="items")['items']
        occupants = []
        for p in participants:
            occupants.append(HipChatMUCRoomOccupant(p))
        return occupants

    def invite(self, *args):
        """
        Invite one or more people into the room.

        :*args:
            One or more people to invite into the room. May be the
            mention name (beginning with an @) or "FirstName LastName"
            of the user you wish to invite.
        """
        room = self.room
        users = self._bot.conn.users

        for person in args:
            try:
                if person.startswith("@"):
                    user = [u for u in users if u['mention_name'] == person[1:]][0]
                else:
                    user = [u for u in users if u['name'] == person][0]
            except IndexError:
                logging.warning("No user by the name of {} found".format(person))
            else:
                if room['privacy'] == "private":
                    room.members().add(user)
                    log.info("Added {} to private room {}".format(user['name'], self))
                room.invite(user, "No reason given.")
                log.info("Invited {} to {}".format(person, self))

    def notify(self, message, color=None, notify=False, message_format=None):
        """
        Send a notification to a room.

        See the
        `HipChat API documentation <https://www.hipchat.com/docs/apiv2/method/send_room_notification>`_
        for more info.
        """
        self.room.notification(
            message=message,
            color=color,
            notify=notify,
            format=message_format
        )


class HipchatClient(XMPPConnection):
    def __init__(self, *args, **kwargs):
        self.token = kwargs.pop('token')
        self.endpoint = kwargs.pop('endpoint')
        if self.endpoint is None:
            self.hypchat = hypchat.HypChat(self.token)
        else:
            # We could always pass in the endpoint, with a default value if it's
            # None, but this way we support hypchat<0.18
            self.hypchat = hypchat.HypChat(self.token, endpoint=self.endpoint)
        super().__init__(*args, **kwargs)

    @property
    def users(self):
        """
        A list of all the users.

        See also: https://www.hipchat.com/docs/apiv2/method/get_all_users
        """
        result = self.hypchat.users(expand='items')
        users = result['items']
        next_link = 'next' in result['links']
        while next_link:
            result = result.next()
            users += result['items']
            next_link = 'next' in result['links']
        return users


class HipchatBackend(XMPPBackend):
    def __init__(self, config):
        self.api_token = config.BOT_IDENTITY['token']
        self.api_endpoint = config.BOT_IDENTITY.get('endpoint', None)
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
            server=self.server
        )

    @property
    def mode(self):
        return 'hipchat'

    def rooms(self):
        """
        Return a list of rooms the bot is currently in.

        :returns:
            A list of :class:`~HipChatMUCRoom` instances.
        """
        xep0045 = self.conn.client.plugin['xep_0045']
        rooms = {}
        # Build a mapping of xmpp_jid->name for easy reference
        for room in self.conn.hypchat.rooms(expand='items')['items']:
            rooms[room['xmpp_jid']] = room['name']

        joined_rooms = []
        for room in xep0045.getJoinedRooms():
            joined_rooms.append(HipChatMUCRoom(rooms[room], self))
        return joined_rooms

    def query_room(self, room):
        """
        Query a room for information.

        :param room:
            The name (preferred) or XMPP JID of the room to query for.
        :returns:
            An instance of :class:`~HipChatMUCRoom`.
        """
        if room.endswith('@conf.hipchat.com'):
            log.debug("Room specified by JID, looking up room name")
            rooms = self.conn.hypchat.rooms(expand='items')
            try:
                name = [r['name'] for r in rooms['items'] if r['xmpp_jid'] == room][0]
            except IndexError:
                raise RoomDoesNotExistError("No room with JID {} found.".format(room))
            log.info("Found {} to be the room {}, consider specifying this directly.".format(room, name))
        else:
            name = room

        return HipChatMUCRoom(name, self)

    def prefix_groupchat_reply(self, message, identifier):
        message.body = '@{0} {1}'.format(identifier.nick, message.body)
