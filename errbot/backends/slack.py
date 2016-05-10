import collections
import json
import logging
import re
import time
import sys
import pprint

from errbot.backends.base import Message, Presence, ONLINE, AWAY, Room, RoomError, RoomDoesNotExistError, \
    UserDoesNotExistError, RoomOccupant, Person, Card
from errbot.errBot import ErrBot
from errbot.utils import PY3, split_string_after
from errbot.rendering.slack import slack_markdown_converter


# Can't use __name__ because of Yapsy
log = logging.getLogger('errbot.backends.slack')

try:
    from functools import lru_cache
except ImportError:
    from backports.functools_lru_cache import lru_cache
try:
    from slackclient import SlackClient
except ImportError:
    log.exception("Could not start the Slack back-end")
    log.fatal(
        "You need to install the slackclient package in order to use the Slack "
        "back-end. You should be able to install this package using: "
        "pip install slackclient"
    )
    sys.exit(1)
except SyntaxError:
    if not PY3:
        raise
    log.exception("Could not start the Slack back-end")
    log.fatal(
        "I cannot start the Slack back-end because I cannot import the SlackClient. "
        "Python 3 compatibility on SlackClient is still quite young, you may be "
        "running an old version or perhaps they released a version with a Python "
        "3 regression. As a last resort to fix this, you could try installing the "
        "latest master version from them using: "
        "pip install --upgrade https://github.com/slackhq/python-slackclient/archive/master.zip"
    )
    sys.exit(1)


# The Slack client automatically turns a channel name into a clickable
# link if you prefix it with a #. Other clients receive this link as a
# token matching this regex.
SLACK_CLIENT_CHANNEL_HYPERLINK = re.compile(r'^<#(?P<id>(C|G)[0-9A-Z]+)>$')

# Empirically determined message size limit.
SLACK_MESSAGE_LIMIT = 4096

USER_IS_BOT_HELPTEXT = (
    "Connected to Slack using a bot account, which cannot manage "
    "channels itself (you must invite the bot to channels instead, "
    "it will auto-accept) nor invite people.\n\n"
    "If you need this functionality, you will have to create a "
    "regular user account and connect Err using that account. "
    "For this, you will also need to generate a user token at "
    "https://api.slack.com/web."
)

COLORS = {
    'red': '#FF0000',
    'green': '#008000',
    'yellow': '#FFA500',
    'blue': '#0000FF',
    'white': '#FFFFFF',
    'cyan': '#00FFFF'
}  # Slack doesn't know its colors


class SlackAPIResponseError(RuntimeError):
    """Slack API returned a non-OK response"""

    def __init__(self, *args, error='', **kwargs):
        """
        :param error:
            The 'error' key from the API response data
        """
        self.error = error
        super().__init__(*args, **kwargs)


class SlackPerson(Person):
    """
    This class describes a person on Slack's network.
    """

    def __init__(self, sc, userid=None, channelid=None):
        if userid is not None and userid[0] not in ('U', 'B'):
            raise Exception('This is not a Slack user or bot id: %s (should start with U or B)' % userid)

        if channelid is not None and channelid[0] not in ('D', 'C', 'G'):
            raise Exception('This is not a valid Slack channelid: %s (should start with D, C or G)' % channelid)

        self._userid = userid
        self._channelid = channelid
        self._sc = sc

    @property
    def userid(self):
        return self._userid

    @property
    def username(self):
        """Convert a Slack user ID to their user name"""
        user = self._sc.server.users.find(self._userid)
        if user is None:
            log.error("Cannot find user with ID %s" % self._userid)
            return "<%s>" % self._userid
        return user.name

    @property
    def channelid(self):
        return self._channelid

    @property
    def channelname(self):
        """Convert a Slack channel ID to its channel name"""
        if self._channelid is None:
            return None

        channel = self._sc.server.channels.find(self._channelid)
        if channel is None:
            raise RoomDoesNotExistError("No channel with ID %s exists" % self._channelid)
        return channel.name

    @property
    def domain(self):
        return self._sc.server.domain

    # Compatibility with the generic API.
    client = channelid
    nick = username

    # Override for ACLs
    @property
    def aclattr(self):
        # Note: Don't use str(self) here because that will return
        # an incorrect format from SlackMUCOccupant.
        return "@%s" % self.username

    @property
    def fullname(self):
        """Convert a Slack user ID to their user name"""
        user = self._sc.server.users.find(self._userid)
        if user is None:
            log.error("Cannot find user with ID %s" % self._userid)
            return "<%s>" % self._userid
        return user.real_name

    def __unicode__(self):
        return "@%s" % self.username

    def __str__(self):
        return self.__unicode__()

    def __eq__(self, other):
        return other.userid == self.userid

    @property
    def person(self):
        # Don't use str(self) here because we want SlackRoomOccupant
        # to return just our @username too.
        return "@%s" % self.username


class SlackRoomOccupant(RoomOccupant, SlackPerson):
    """
    This class represents a person inside a MUC.
    """
    def __init__(self, sc, userid, channelid, bot):
        super().__init__(sc, userid, channelid)
        self._room = SlackRoom(channelid=channelid, bot=bot)

    @property
    def room(self):
        return self._room

    def __unicode__(self):
        return "#%s/%s" % (self._room.name, self.username)

    def __str__(self):
        return self.__unicode__()

    def __eq__(self, other):
        if not isinstance(other, RoomOccupant):
            log.warn('tried to compare a SlackRoomOccupant with a SlackPerson %s vs %s', self, other)
            return False
        return other.room.id == self.room.id and other.userid == self.userid


class SlackBackend(ErrBot):
    def __init__(self, config):
        super().__init__(config)
        identity = config.BOT_IDENTITY
        self.token = identity.get('token', None)
        if not self.token:
            log.fatal(
                'You need to set your token (found under "Bot Integration" on Slack) in '
                'the BOT_IDENTITY setting in your configuration. Without this token I '
                'cannot connect to Slack.'
            )
            sys.exit(1)
        self.sc = None  # Will be initialized in serve_once
        compact = config.COMPACT_OUTPUT if hasattr(config, 'COMPACT_OUTPUT') else False
        self.md = slack_markdown_converter(compact)

    def api_call(self, method, data=None, raise_errors=True):
        """
        Make an API call to the Slack API and return response data.

        This is a thin wrapper around `SlackClient.server.api_call`.

        :param method:
            The API method to invoke (see https://api.slack.com/methods/).
        :param raise_errors:
            Whether to raise :class:`~SlackAPIResponseError` if the API
            returns an error
        :param data:
            A dictionary with data to pass along in the API request.
        :returns:
            A dictionary containing the (JSON-decoded) API response
        :raises:
            :class:`~SlackAPIResponseError` if raise_errors is True and the
            API responds with `{"ok": false}`
        """
        if data is None:
            data = {}
        response = self.sc.api_call(method, **data)
        if not isinstance(response, collections.Mapping):
            # Compatibility with SlackClient < 1.0.0
            response = json.loads(response.decode('utf-8'))

        if raise_errors and not response['ok']:
            raise SlackAPIResponseError(
                "Slack API call to %s failed: %s" % (method, response['error']),
                error=response['error']
            )
        return response

    def serve_once(self):
        self.sc = SlackClient(self.token)
        log.info("Verifying authentication token")
        self.auth = self.api_call("auth.test", raise_errors=False)
        if not self.auth['ok']:
            raise SlackAPIResponseError(error="Couldn't authenticate with Slack. Server said: %s" % self.auth['error'])
        log.debug("Token accepted")
        self.bot_identifier = SlackPerson(self.sc, self.auth["user_id"])

        log.info("Connecting to Slack real-time-messaging API")
        if self.sc.rtm_connect():
            log.info("Connected")
            self.reset_reconnection_count()
            try:
                while True:
                    for message in self.sc.rtm_read():
                        self._dispatch_slack_message(message)
                    time.sleep(1)
            except KeyboardInterrupt:
                log.info("Interrupt received, shutting down..")
                return True
            except:
                log.exception("Error reading from RTM stream:")
            finally:
                log.debug("Triggering disconnect callback")
                self.disconnect_callback()
        else:
            raise Exception('Connection failed, invalid token ?')

    def _dispatch_slack_message(self, message):
        """
        Process an incoming message from slack.

        """
        if 'type' not in message:
            log.debug("Ignoring non-event message: %s" % message)
            return

        event_type = message['type']

        event_handlers = {
            'hello': self._hello_event_handler,
            'presence_change': self._presence_change_event_handler,
            'message': self._message_event_handler,
        }

        event_handler = event_handlers.get(event_type)

        if event_handler is None:
            log.debug("No event handler available for %s, ignoring this event" % event_type)
            return
        try:
            log.debug("Processing slack event: %s" % message)
            event_handler(message)
        except Exception:
            log.exception("%s event handler raised an exception" % event_type)

    def _hello_event_handler(self, event):
        """Event handler for the 'hello' event"""
        self.connect_callback()
        self.callback_presence(Presence(identifier=self.bot_identifier, status=ONLINE))

    def _presence_change_event_handler(self, event):
        """Event handler for the 'presence_change' event"""

        idd = SlackPerson(self.sc, event['user'])
        presence = event['presence']
        # According to https://api.slack.com/docs/presence, presence can
        # only be one of 'active' and 'away'
        if presence == 'active':
            status = ONLINE
        elif presence == 'away':
            status = AWAY
        else:
            log.error(
                "It appears the Slack API changed, I received an unknown presence type %s" % presence
            )
            status = ONLINE
        self.callback_presence(Presence(identifier=idd, status=status))

    def _message_event_handler(self, event):
        """Event handler for the 'message' event"""
        channel = event['channel']
        if channel[0] not in 'CGD':
            log.warning("Unknown message type! Unable to handle %s", channel)
            return

        subtype = event.get('subtype', None)

        if subtype == "message_deleted":
            log.debug("Message of type message_deleted, ignoring this event")
            return
        if subtype == "message_changed" and 'attachments' in event['message']:
            # If you paste a link into Slack, it does a call-out to grab details
            # from it so it can display this in the chatroom. These show up as
            # message_changed events with an 'attachments' key in the embedded
            # message. We should completely ignore these events otherwise we
            # could end up processing bot commands twice (user issues a command
            # containing a link, it gets processed, then Slack triggers the
            # message_changed event and we end up processing it again as a new
            # message. This is not what we want).
            log.debug(
                "Ignoring message_changed event with attachments, likely caused "
                "by Slack auto-expanding a link"
            )
            return

        if 'message' in event:
            text = event['message']['text']
            user = event['message'].get('user', event.get('bot_id'))
        else:
            text = event['text']
            user = event.get('user', event.get('bot_id'))

        mentioned = []

        for word in text.split():
            if word.startswith('<') or word.startswith('@') or word.startswith('#'):
                try:
                    identifier = self.build_identifier(word.replace(':', ''))
                except Exception as e:
                    log.debug("Tried to build an identifier from '%s' but got exception: %s", word, e)
                    continue
                log.debug('Someone mentioned')
                mentioned.append(identifier)
                text = re.sub('<@[^>]*>:*', '@%s' % mentioned[-1].username, text)

        text = self.sanitize_uris(text)

        log.debug("Saw an event: %s" % pprint.pformat(event))
        log.debug("Escaped IDs event text: %s" % text)

        msg = Message(
            text,
            extras={'attachments': event.get('attachments')})

        if channel.startswith('D'):
            msg.frm = SlackPerson(self.sc, user, event['channel'])
            msg.to = SlackPerson(self.sc, self.username_to_userid(self.sc.server.username),
                                 event['channel'])
        else:
            msg.frm = SlackRoomOccupant(self.sc, user, event['channel'], bot=self)
            msg.to = SlackRoom(channelid=event['channel'], bot=self)

        self.callback_message(msg)

        if mentioned:
            self.callback_mention(msg, mentioned)

    def userid_to_username(self, id_):
        """Convert a Slack user ID to their user name"""
        user = [user for user in self.sc.server.users if user.id == id_]
        if not user:
            raise UserDoesNotExistError("Cannot find user with ID %s" % id_)
        return user[0].name

    def username_to_userid(self, name):
        """Convert a Slack user name to their user ID"""
        user = [user for user in self.sc.server.users if user.name == name]
        if not user:
            raise UserDoesNotExistError("Cannot find user %s" % name)
        return user[0].id

    def channelid_to_channelname(self, id_):
        """Convert a Slack channel ID to its channel name"""
        channel = [channel for channel in self.sc.server.channels if channel.id == id_]
        if not channel:
            raise RoomDoesNotExistError("No channel with ID %s exists" % id_)
        return channel[0].name

    def channelname_to_channelid(self, name):
        """Convert a Slack channel name to its channel ID"""
        if name.startswith('#'):
            name = name[1:]
        channel = [channel for channel in self.sc.server.channels if channel.name == name]
        if not channel:
            raise RoomDoesNotExistError("No channel named %s exists" % name)
        return channel[0].id

    def channels(self, exclude_archived=True, joined_only=False):
        """
        Get all channels and groups and return information about them.

        :param exclude_archived:
            Exclude archived channels/groups
        :param joined_only:
            Filter out channels the bot hasn't joined
        :returns:
            A list of channel (https://api.slack.com/types/channel)
            and group (https://api.slack.com/types/group) types.

        See also:
          * https://api.slack.com/methods/channels.list
          * https://api.slack.com/methods/groups.list
        """
        response = self.api_call('channels.list', data={'exclude_archived': exclude_archived})
        channels = [channel for channel in response['channels']
                    if channel['is_member'] or not joined_only]

        response = self.api_call('groups.list', data={'exclude_archived': exclude_archived})
        # No need to filter for 'is_member' in this next call (it doesn't
        # (even exist) because leaving a group means you have to get invited
        # back again by somebody else.
        groups = [group for group in response['groups']]

        return channels + groups

    @lru_cache(50)
    def get_im_channel(self, id_):
        """Open a direct message channel to a user"""
        response = self.api_call('im.open', data={'user': id_})
        return response['channel']['id']

    def _prepare_message(self, mess):  # or card
        """
        Translates the common part of messaging for Slack.
        :param mess: the message you want to extract the Slack concept from.
        :return: a tuple to user human readable, the channel id
        """
        if mess.is_group:
            to_channel_id = mess.to.id
            to_humanreadable = mess.to.name if mess.to.name else self.channelid_to_channelname(to_channel_id)
        else:
            to_humanreadable = mess.to.username
            to_channel_id = mess.to.channelid
            if to_channel_id.startswith('C'):
                log.debug("This is a divert to private message, sending it directly to the user.")
                to_channel_id = self.get_im_channel(self.username_to_userid(mess.to.username))
        return to_humanreadable, to_channel_id

    def send_message(self, mess):
        super().send_message(mess)
        to_humanreadable = "<unknown>"
        try:
            if mess.is_group:
                to_channel_id = mess.to.id
                to_humanreadable = mess.to.name if mess.to.name else self.channelid_to_channelname(to_channel_id)
            else:
                to_humanreadable = mess.to.username
                if isinstance(mess.to, RoomOccupant):  # private to a room occupant -> this is a divert to private !
                    log.debug("This is a divert to private message, sending it directly to the user.")
                    to_channel_id = self.get_im_channel(self.username_to_userid(mess.to.username))
                else:
                    to_channel_id = mess.to.channelid

            msgtype = "direct" if mess.is_direct else "channel"
            log.debug('Sending %s message to %s (%s)' % (msgtype, to_humanreadable, to_channel_id))

            body = self.md.convert(mess.body)
            log.debug('Message size: %d' % len(body))

            limit = min(self.bot_config.MESSAGE_SIZE_LIMIT, SLACK_MESSAGE_LIMIT)
            parts = self.prepare_message_body(body, limit)

            for part in parts:
                self.api_call('chat.postMessage', data={
                    'channel': to_channel_id,
                    'text': part,
                    'unfurl_media': 'true',
                    'as_user': 'true',
                })
        except Exception:
            log.exception(
                "An exception occurred while trying to send the following message "
                "to %s: %s" % (to_humanreadable, mess.body)
            )

    def send_card(self, card: Card):
        try:
            if isinstance(card.to, RoomOccupant):
                card.to = card.to.room
            to_humanreadable, to_channel_id = self._prepare_message(card)
            attachment = {}
            if card.summary:
                attachment['pretext'] = card.summary
            if card.title:
                attachment['title'] = card.title
            if card.link:
                attachment['title_link'] = card.link
            if card.image:
                attachment['image_url'] = card.image
            if card.thumbnail:
                attachment['thumb_url'] = card.thumbnail
            attachment['text'] = card.body

            if card.color:
                attachment['color'] = COLORS[card.color] if card.color in COLORS else card.color

            if card.fields:
                attachment['fields'] = [{'title': key, 'value': value, 'short': True} for key, value in card.fields]

            data = {'text': ' ', 'channel': to_channel_id, 'attachments': json.dumps([attachment]), 'as_user': 'true'}
            log.debug('Sending data:\n%s', data)
            self.api_call('chat.postMessage', data=data)
        except Exception:
            log.exception(
                "An exception occurred while trying to send a card to %s.[%s]" % (to_humanreadable, card)
            )

    def __hash__(self):
        return 0  # this is a singleton anyway

    def change_presence(self, status: str = ONLINE, message: str = '') -> None:
        self.api_call('users.setPresence', data={'presence': 'auto' if status == ONLINE else 'away'})

    @staticmethod
    def prepare_message_body(body, size_limit):
        """
        Returns the parts of a message chunked and ready for sending.

        This is a staticmethod for easier testing.

        Args:
            body (str)
            size_limit (int): chunk the body into sizes capped at this maximum

        Returns:
            [str]

        """
        fixed_format = body.startswith('```')  # hack to fix the formatting
        parts = list(split_string_after(body, size_limit))

        if len(parts) == 1:
            # If we've got an open fixed block, close it out
            if parts[0].count('```') % 2 != 0:
                parts[0] += '\n```\n'
        else:
            for i, part in enumerate(parts):
                starts_with_code = part.startswith('```')

                # If we're continuing a fixed block from the last part
                if fixed_format and not starts_with_code:
                    parts[i] = '```\n' + part

                # If we've got an open fixed block, close it out
                if part.count('```') % 2 != 0:
                    parts[i] += '\n```\n'

        return parts

    @staticmethod
    def extract_identifiers_from_string(text):
        """
        Parse a string for Slack user/channel IDs.

        Supports strings with the following formats::

            <#C12345>
            <@U12345>
            @user
            #channel/user
            #channel

        Returns the tuple (username, userid, channelname, channelid).
        Some elements may come back as None.
        """
        exception_message = (
            "Unparseable slack identifier, should be of the format `<#C12345>`, `<@U12345>`, "
            "`@user`, `#channel/user` or `#channel`. (Got `%s`)"
        )
        text = text.strip()

        if text == "":
            raise ValueError(exception_message % "")

        channelname = None
        username = None
        channelid = None
        userid = None

        if text[0] == "<" and text[-1] == ">":
            exception_message = (
                "Unparseable slack ID, should start with U, B, C, G or D "
                "(got `%s`)"
            )
            text = text[2:-1]
            if text == "":
                raise ValueError(exception_message % "")
            if text[0] in ('U', 'B'):
                userid = text
            elif text[0] in ('C', 'G', 'D'):
                channelid = text
            else:
                raise ValueError(exception_message % text)
        elif text[0] == '@':
            username = text[1:]
        elif text[0] == '#':
            plainrep = text[1:]
            if '/' in text:
                channelname, username = plainrep.split('/', 1)
            else:
                channelname = plainrep
        else:
            raise ValueError(exception_message % text)

        return username, userid, channelname, channelid

    def build_identifier(self, txtrep):
        """
        Build a :class:`SlackIdentifier` from the given string txtrep.

        Supports strings with the formats accepted by
        :func:`~extract_identifiers_from_string`.
        """
        log.debug("building an identifier from %s" % txtrep)
        username, userid, channelname, channelid = self.extract_identifiers_from_string(txtrep)

        if userid is not None:
            return SlackPerson(self.sc, userid, self.get_im_channel(userid))
        if channelid is not None:
            return SlackPerson(self.sc, None, channelid)
        if username is not None:
            userid = self.username_to_userid(username)
            return SlackPerson(self.sc, userid, self.get_im_channel(userid))
        if channelname is not None:
            channelid = self.channelname_to_channelid(channelname)
            return SlackRoomOccupant(self.sc, userid, channelid, bot=self)

        raise Exception(
            "You found a bug. I expected at least one of userid, channelid, username or channelname "
            "to be resolved but none of them were. This shouldn't happen so, please file a bug."
        )

    def build_reply(self, mess, text=None, private=False):
        response = self.build_message(text)
        response.frm = self.bot_identifier
        if private:
            response.to = mess.frm
        else:
            response.to = mess.frm.room if isinstance(mess.frm, RoomOccupant) else mess.frm
        return response

    def shutdown(self):
        super().shutdown()

    @property
    def mode(self):
        return 'slack'

    def query_room(self, room):
        """ Room can either be a name or a channelid """
        if room.startswith('C') or room.startswith('G'):
            return SlackRoom(channelid=room, bot=self)

        m = SLACK_CLIENT_CHANNEL_HYPERLINK.match(room)
        if m is not None:
            return SlackRoom(channelid=m.groupdict()['id'], bot=self)

        return SlackRoom(name=room, bot=self)

    def rooms(self):
        """
        Return a list of rooms the bot is currently in.

        :returns:
            A list of :class:`~SlackRoom` instances.
        """
        channels = self.channels(joined_only=True, exclude_archived=True)
        return [SlackRoom(channelid=channel['id'], bot=self) for channel in channels]

    def prefix_groupchat_reply(self, message, identifier):
        super().prefix_groupchat_reply(message, identifier)
        message.body = '@{0}: {1}'.format(identifier.nick, message.body)

    @staticmethod
    def sanitize_uris(text):
        """
        Sanitizes URI's present within a slack message. e.g.
        <mailto:example@example.org|example@example.org>,
        <http://example.org|example.org>
        <http://example.org>

        :returns:
            string
        """
        text = re.sub(r'<([^\|>]+)\|([^\|>]+)>', r'\2', text)
        text = re.sub(r'<(http([^\>]+))>', r'\1', text)

        return text


class SlackRoom(Room):
    def __init__(self, name=None, channelid=None, bot=None):
        if channelid is not None and name is not None:
            raise ValueError("channelid and name are mutually exclusive")

        if name is not None:
            if name.startswith('#'):
                self._name = name[1:]
            else:
                self._name = name
        else:
            self._name = bot.channelid_to_channelname(channelid)

        self._id = None
        self._bot = bot
        self.sc = bot.sc

    def __str__(self):
        return "#%s" % self.name

    @property
    def _channel(self):
        """
        The channel object exposed by SlackClient
        """
        id_ = self.sc.server.channels.find(self.name)
        if id_ is None:
            raise RoomDoesNotExistError(
                "%s does not exist (or is a private group you don't have access to)" % str(self)
            )
        return id_

    @property
    def _channel_info(self):
        """
        Channel info as returned by the Slack API.

        See also:
          * https://api.slack.com/methods/channels.list
          * https://api.slack.com/methods/groups.list
        """
        if self.private:
            return self._bot.api_call('groups.info', data={'channel': self.id})["group"]
        else:
            return self._bot.api_call('channels.info', data={'channel': self.id})["channel"]

    @property
    def private(self):
        """Return True if the room is a private group"""
        return self._channel.id.startswith('G')

    @property
    def id(self):
        """Return the ID of this room"""
        if self._id is None:
            self._id = self._channel.id
        return self._id

    @property
    def name(self):
        """Return the name of this room"""
        return self._name

    def join(self, username=None, password=None):
        log.info("Joining channel %s" % str(self))
        try:
            self._bot.api_call('channels.join', data={'name': self.name})
        except SlackAPIResponseError as e:
            if e.error == "user_is_bot":
                raise RoomError("Unable to join channel. " + USER_IS_BOT_HELPTEXT)
            else:
                raise RoomError(e)

    def leave(self, reason=None):
        try:
            if self.id.startswith('C'):
                log.info("Leaving channel %s (%s)" % (str(self), self.id))
                self._bot.api_call('channels.leave', data={'channel': self.id})
            else:
                log.info("Leaving group %s (%s)" % (str(self), self.id))
                self._bot.api_call('groups.leave', data={'channel': self.id})
        except SlackAPIResponseError as e:
            if e.error == "user_is_bot":
                raise RoomError("Unable to leave channel. " + USER_IS_BOT_HELPTEXT)
            else:
                raise RoomError(e)
        self._id = None

    def create(self, private=False):
        try:
            if private:
                log.info("Creating group %s" % str(self))
                self._bot.api_call('groups.create', data={'name': self.name})
            else:
                log.info("Creating channel %s" % str(self))
                self._bot.api_call('channels.create', data={'name': self.name})
        except SlackAPIResponseError as e:
            if e.error == "user_is_bot":
                raise RoomError("Unable to create channel. " + USER_IS_BOT_HELPTEXT)
            else:
                raise RoomError(e)

    def destroy(self):
        try:
            if self.id.startswith('C'):
                log.info("Archiving channel %s (%s)" % (str(self), self.id))
                self._bot.api_call('channels.archive', data={'channel': self.id})
            else:
                log.info("Archiving group %s (%s)" % (str(self), self.id))
                self._bot.api_call('groups.archive', data={'channel': self.id})
        except SlackAPIResponseError as e:
            if e.error == "user_is_bot":
                raise RoomError("Unable to archive channel. " + USER_IS_BOT_HELPTEXT)
            else:
                raise RoomError(e)
        self._id = None

    @property
    def exists(self):
        channels = self._bot.channels(joined_only=False, exclude_archived=False)
        return len([c for c in channels if c['name'] == self.name]) > 0

    @property
    def joined(self):
        channels = self._bot.channels(joined_only=True)
        return len([c for c in channels if c['name'] == self.name]) > 0

    @property
    def topic(self):
        if self._channel_info['topic']['value'] == '':
            return None
        else:
            return self._channel_info['topic']['value']

    @topic.setter
    def topic(self, topic):
        if self.private:
            log.info("Setting topic of %s (%s) to '%s'" % (str(self), self.id, topic))
            self._bot.api_call('groups.setTopic', data={'channel': self.id, 'topic': topic})
        else:
            log.info("Setting topic of %s (%s) to '%s'" % (str(self), self.id, topic))
            self._bot.api_call('channels.setTopic', data={'channel': self.id, 'topic': topic})

    @property
    def purpose(self):
        if self._channel_info['purpose']['value'] == '':
            return None
        else:
            return self._channel_info['purpose']['value']

    @purpose.setter
    def purpose(self, purpose):
        if self.private:
            log.info("Setting purpose of %s (%s) to '%s'" % (str(self), self.id, purpose))
            self._bot.api_call('groups.setPurpose', data={'channel': self.id, 'purpose': purpose})
        else:
            log.info("Setting purpose of %s (%s) to '%s'" % (str(self), self.id, purpose))
            self._bot.api_call('channels.setPurpose', data={'channel': self.id, 'purpose': purpose})

    @property
    def occupants(self):
        members = self._channel_info['members']
        return [SlackRoomOccupant(self.sc, m, self.id, self._bot) for m in members]

    def invite(self, *args):
        users = {user['name']: user['id'] for user in self._bot.api_call('users.list')['members']}
        for user in args:
            if user not in users:
                raise UserDoesNotExistError("User '%s' not found" % user)
            log.info("Inviting %s into %s (%s)" % (user, str(self), self.id))
            method = 'groups.invite' if self.private else 'channels.invite'
            response = self._bot.api_call(
                method,
                data={'channel': self.id, 'user': users[user]},
                raise_errors=False
            )

            if not response['ok']:
                if response['error'] == "user_is_bot":
                    raise RoomError("Unable to invite people. " + USER_IS_BOT_HELPTEXT)
                elif response['error'] != "already_in_channel":
                    raise SlackAPIResponseError(error="Slack API call to %s failed: %s" % (method, response['error']))

    def __eq__(self, other):
        return self.id == other.id
