import logging

from errbot import BotPlugin, botcmd, SeparatorArgParser, ShlexArgParser
from errbot.backends.base import RoomNotJoinedError
from errbot.utils import compat_str, PY3

# 2to3 hack
# thanks to https://github.com/oxplot/fysom/issues/1
# which in turn references http://www.rfk.id.au/blog/entry/preparing-pyenchant-for-python-3/
if PY3:
    basestring = (str, bytes)

log = logging.getLogger(__name__)
log.debug("LOADING CHATROOM")


class ChatRoom(BotPlugin):

    connected = False

    def callback_connect(self):
        self.log.info('Callback_connect')
        if not self.connected:
            self.connected = True
            for room in self.bot_config.CHATROOM_PRESENCE:
                self.log.debug('Try to join room %s' % repr(room))
                try:
                    self._join_room(room)
                except Exception:
                    # Ensure failure to join a room doesn't crash the plugin
                    # as a whole.
                    self.log.exception("Joining room %s failed", repr(room))

    def _join_room(self, room):
        if isinstance(room, (tuple, list)):
            room_name = compat_str(room[0])
            room_password = compat_str(room[1])
            room, username, password = (room_name, self.bot_config.CHATROOM_FN, room_password)
            self.log.info("Joining room {} with username {} and password".format(room, username))
        else:
            room_name = compat_str(room)
            room, username, password = (room_name, self.bot_config.CHATROOM_FN, None)
            self.log.info("Joining room {} with username {}".format(room, username))
            self.query_room(room).join(username=self.bot_config.CHATROOM_FN, password=password)

    def deactivate(self):
        self.connected = False
        super().deactivate()

    @botcmd(split_args_with=SeparatorArgParser())
    def room_create(self, message, args):
        """
        Create a chatroom.

        Usage:
        !room create <room>

        Examples (XMPP):
        !room create example-room@chat.server.tld

        Examples (IRC):
        !room create #example-room
        """
        if len(args) < 1:
            return "Please tell me which chatroom to create."
        room = self.query_room(args[0])
        room.create()
        return "Created the room {}".format(room)

    @botcmd()
    def room_join(self, message, args):
        """
        Join (creating it first if needed) a chatroom.

        Usage:
        !room join <room> [<password>]

        Examples (XMPP):
        !room join example-room@chat.server.tld
        !room join example-room@chat.server.tld super-secret-password

        Examples (IRC):
        !room join #example-room
        !room join #example-room super-secret-password
        """
        # We must account for password with whitespace before, after or in the middle
        args = args.split(' ', 1)
        arglen = len(args)
        if arglen < 1:
            return "Please tell me which chatroom to join."
        args[0].strip()

        room, password = (args[0], None) if arglen == 1 else (args[0], args[1])
        self.query_room(room).join(username=self.bot_config.CHATROOM_FN, password=password)
        return "Joined the room {}".format(room)

    @botcmd(split_args_with=SeparatorArgParser())
    def room_leave(self, message, args):
        """
        Leave a chatroom.

        Usage:
        !room leave <room>

        Examples (XMPP):
        !room leave example-room@chat.server.tld

        Examples (IRC):
        !room leave #example-room
        """
        if len(args) < 1:
            return "Please tell me which chatroom to leave."
        self.query_room(args[0]).leave()
        return "Left the room {}".format(args[0])

    @botcmd(split_args_with=SeparatorArgParser())
    def room_destroy(self, message, args):
        """
        Destroy a chatroom.

        Usage:
        !room destroy <room>

        Examples (XMPP):
        !room destroy example-room@chat.server.tld

        Examples (IRC):
        !room destroy #example-room
        """
        if len(args) < 1:
            return "Please tell me which chatroom to destroy."
        self.query_room(args[0]).destroy()
        return "Destroyed the room {}".format(args[0])

    @botcmd(split_args_with=SeparatorArgParser())
    def room_invite(self, message, args):
        """
        Invite one or more people into a chatroom.

        Usage:
        !room invite <room> <identifier1> [<identifier2>, ..]

        Examples (XMPP):
        !room invite room@conference.server.tld bob@server.tld

        Examples (IRC):
        !room invite #example-room bob
        """
        if len(args) < 2:
            return "Please tell me which person(s) to invite into which room."
        self.query_room(args[0]).invite(*args[1:])
        return "Invited {} into the room {}".format(", ".join(args[1:]), args[0])

    @botcmd
    def room_list(self, message, args):
        """
        List chatrooms the bot has joined.

        Usage:
        !room list

        Examples:
        !room list
        """
        rooms = [str(room) for room in self.rooms()]
        if len(rooms):
            return "I'm currently in these rooms:\n\t{}".format("\n\t".join(rooms))
        else:
            return "I'm not currently in any rooms."

    @botcmd(split_args_with=ShlexArgParser())
    def room_occupants(self, message, args):
        """
        List the occupants in a given chatroom.

        Usage:
        !room occupants <room 1> [<room 2> ..]

        Examples (XMPP):
        !room occupants room@conference.server.tld

        Examples (IRC):
        !room occupants #example-room #another-example-room
        """
        if len(args) < 1:
            yield "Please supply a room to list the occupants of."
            return
        for room in args:
            try:
                occupants = [o.person for o in self.query_room(room).occupants]
                yield "Occupants in {}:\n\t{}".format(room, "\n\t".join(occupants))
            except RoomNotJoinedError as e:
                yield "Cannot list occupants in {}: {}".format(room, e)

    @botcmd(split_args_with=ShlexArgParser())
    def room_topic(self, message, args):
        """
        Get or set the topic for a room.

        Usage:
        !room topic <room> [<new topic>]

        Examples (XMPP):
        !room topic example-room@chat.server.tld
        !room topic example-room@chat.server.tld "Err rocks!"

        Examples (IRC):
        !room topic #example-room
        !room topic #example-room "Err rocks!"
        """
        arglen = len(args)
        if arglen < 1:
            return "Please tell me which chatroom you want to know the topic of."

        if arglen == 1:
            try:
                topic = self.query_room(args[0]).topic
            except RoomNotJoinedError as e:
                return "Cannot get the topic for {}: {}".format(args[0], e)
            if topic is None:
                return "No topic is set for {}".format(args[0])
            else:
                return "Topic for {}: {}".format(args[0], topic)
        else:
            try:
                self.query_room(args[0]).topic = args[1]
            except RoomNotJoinedError as e:
                return "Cannot set the topic for {}: {}".format(args[0], e)
            return "Topic for {} set.".format(args[0])

    def callback_message(self, mess):
        try:
            if mess.is_direct:
                username = mess.frm.person
                if username in self.bot_config.CHATROOM_RELAY:
                    self.log.debug('Message to relay from %s.' % username)
                    body = mess.body
                    rooms = self.bot_config.CHATROOM_RELAY[username]
                    for roomstr in rooms:
                        room = self.room_join(roomstr)
                        self.send(room, body)
            elif mess.is_group:
                fr = mess.frm
                chat_room = str(fr.room)
                if chat_room in self.bot_config.REVERSE_CHATROOM_RELAY:
                    users_to_relay_to = self.bot_config.REVERSE_CHATROOM_RELAY[chat_room]
                    self.log.debug('Message to relay to %s.' % users_to_relay_to)
                    body = '[%s] %s' % (fr.person, mess.body)
                    for user in users_to_relay_to:
                        self.send(user, body)
        except Exception as e:
            self.log.exception('crashed in callback_message %s' % e)
