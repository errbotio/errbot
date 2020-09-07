from time import sleep

import copyreg
import json
import logging
import re
import sys
import pprint
from functools import lru_cache
from typing import BinaryIO

from markdown import Markdown
from markdown.extensions.extra import ExtraExtension
from markdown.preprocessors import Preprocessor

from errbot.backends.base import Identifier, Message, Presence, ONLINE, AWAY, Room, RoomError, RoomDoesNotExistError, \
    UserDoesNotExistError, RoomOccupant, Person, Card, Stream
from errbot.core import ErrBot
from errbot.utils import split_string_after
from errbot.rendering.ansiext import AnsiExtension, enable_format, IMTEXT_CHRS
from errbot import webhook
from errbot.core_plugins import flask_app

log = logging.getLogger(__name__)

from slack_rtm import slack_markdown_converter, SlackAPIResponseError, SlackRoomOccupant, SlackBot, SlackRoom, SLACK_CLIENT_CHANNEL_HYPERLINK, SLACK_MESSAGE_LIMIT, COLORS, SlackPerson

try:
    from slackeventsapi import SlackEventAdapter
    from slack.errors import BotUserAccessError
    from slack import WebClient
except ImportError:
    log.exception("Could not start the SlackRTM backend")
    log.fatal(
        "You need to install slackclient in order to use the Slack backend.\n"
        "You can do `pip install errbot[slack-events]` to install it."
    )
    sys.exit(1)


class SlackEventsBackend(ErrBot):

    @staticmethod
    def _unpickle_identifier(identifier_str):
        return SlackEventsBackend.__build_identifier(identifier_str)

    @staticmethod
    def _pickle_identifier(identifier):
        return SlackEventsBackend._unpickle_identifier, (str(identifier),)

    def _register_identifiers_pickling(self):
        """
        Register identifiers pickling.

        As Slack needs live objects in its identifiers, we need to override their pickling behavior.
        But for the unpickling to work we need to use bot.build_identifier, hence the bot parameter here.
        But then we also need bot for the unpickling so we save it here at module level.
        """
        SlackEventsBackend.__build_identifier = self.build_identifier
        for cls in (SlackPerson, SlackRoomOccupant, SlackRoom):
            copyreg.pickle(cls, SlackEventsBackend._pickle_identifier, SlackEventsBackend._unpickle_identifier)

    def __init__(self, config):
        super().__init__(config)
        identity = config.BOT_IDENTITY
        self.token = identity.get('token', None)
        self.signing_secret = identity.get('signing_secret', None)
        self.proxies = identity.get('proxies', None)
        if not self.token:
            log.fatal(
                'You need to set your token (found under "Bot Integration" on Slack) in '
                'the BOT_IDENTITY setting in your configuration. Without this token I '
                'cannot connect to Slack.'
            )
            sys.exit(1)
        if not self.signing_secret:
            log.fatal(
                'You need to set your signing_secret (found under "Bot Integration" on Slack) in '
                'the BOT_IDENTITY setting in your configuration. Without this secret I '
                'cannot receive events from Slack.'
            )
            sys.exit(1)
        self.sc = None  # Will be initialized in serve_once
        self.slack_events_adapter = None  # Will be initialized in serve_once
        self.webclient = None
        self.bot_identifier = None
        compact = config.COMPACT_OUTPUT if hasattr(config, 'COMPACT_OUTPUT') else False
        self.md = slack_markdown_converter(compact)
        self._register_identifiers_pickling()

    def update_alternate_prefixes(self):
        """Converts BOT_ALT_PREFIXES to use the slack ID instead of name

        Slack only acknowledges direct callouts `@username` in chat if referred
        by using the ID of that user.
        """
        # convert BOT_ALT_PREFIXES to a list
        try:
            bot_prefixes = self.bot_config.BOT_ALT_PREFIXES.split(',')
        except AttributeError:
            bot_prefixes = list(self.bot_config.BOT_ALT_PREFIXES)

        converted_prefixes = []
        for prefix in bot_prefixes:
            try:
                converted_prefixes.append(f'<@{self.username_to_userid(self.webclient, prefix)}>')
            except Exception as e:
                log.error('Failed to look up Slack userid for alternate prefix "%s": %s', prefix, e)

        self.bot_alt_prefixes = tuple(x.lower() for x in self.bot_config.BOT_ALT_PREFIXES)
        log.debug('Converted bot_alt_prefixes: %s', self.bot_config.BOT_ALT_PREFIXES)

    def _setup_event_callbacks(self):
        self.connect_callback()
        self.slack_events_adapter.on('reaction_added', self.reaction_added)
        self.slack_events_adapter.on('message', self._message_event_handler)
        self.slack_events_adapter.on('member_joined_channel', self._member_joined_channel_event_handler)
        self.slack_events_adapter.on('presence_change', self._presence_change_event_handler)

    # Create an event listener for "reaction_added" events and print the emoji name
    def reaction_added(self, event_data):
      emoji = event_data["event"]["reaction"]
      log.debug('Recived event: {}'.format(str(event_data)))
      log.debug('Emoji: {}'.format(emoji))

    def serve_forever(self):
        self.sc = WebClient(token=self.token, proxy=self.proxies)
        self.webclient = self.sc
        self.slack_events_adapter = SlackEventAdapter(self.signing_secret, "/slack/events", flask_app)

        log.info('Verifying authentication token')
        self.auth = self.sc.auth_test()
        log.debug(f"Auth response: {self.auth}")
        if not self.auth['ok']:
            raise SlackAPIResponseError(error=f"Couldn't authenticate with Slack. Server said: {self.auth['error']}")
        log.debug("Token accepted")
        self._setup_event_callbacks()

        self.bot_identifier = SlackPerson(self.sc, self.auth['user_id'])

        log.debug(self.bot_identifier)

        # Inject bot identity to alternative prefixes
        self.update_alternate_prefixes()

        log.debug('Initialized, waiting for events')
        try:
            while True:
                sleep(1)
        except KeyboardInterrupt:
            log.info("Interrupt received, shutting down..")
            return True
        except Exception:
            log.exception("Error reading from RTM stream:")
        finally:
            log.debug("Triggering disconnect callback")
            self.disconnect_callback()

    def _presence_change_event_handler(self, raw_event):
        """Event handler for the 'presence_change' event"""

        log.debug('Saw an event: %s', pprint.pformat(raw_event))
        event = raw_event['event']
        idd = SlackPerson(webclient, event['user'])
        presence = event['presence']
        # According to https://api.slack.com/docs/presence, presence can
        # only be one of 'active' and 'away'
        if presence == 'active':
            status = ONLINE
        elif presence == 'away':
            status = AWAY
        else:
            log.error(f'It appears the Slack API changed, I received an unknown presence type {presence}.')
            status = ONLINE
        self.callback_presence(Presence(identifier=idd, status=status))

    def _message_event_handler(self, raw_event):
        """Event handler for the 'message' event"""
        log.debug('Saw an event: %s', pprint.pformat(raw_event))
        event = raw_event['event']
        channel = event['channel']
        if channel[0] not in 'CGD':
            log.warning("Unknown message type! Unable to handle %s", channel)
            return

        subtype = event.get('subtype', None)

        if subtype in ("message_deleted", "channel_topic", "message_replied"):
            log.debug("Message of type %s, ignoring this event", subtype)
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
        if subtype == "message_changed":
            event = event['message']
        text = event['text']

        text, mentioned = self.process_mentions(text)

        text = self.sanitize_uris(text)

        log.debug('Escaped IDs event text: %s', text)

        msg = Message(
            text,
            extras={
                'attachments': event.get('attachments'),
                'slack_event': event,
            },
        )

        if channel.startswith('D'):
            if subtype == "bot_message":
                msg.frm = SlackBot(
                    self.sc,
                    bot_id=event.get('bot_id'),
                    bot_username=event.get('username', '')
                )
            else:
                msg.frm = SlackPerson(self.sc, event['user'], channel)
            msg.to = SlackPerson(self.sc, self.bot_identifier.userid, channel)
            channel_link_name = channel
        else:
            if subtype == "bot_message":
                msg.frm = SlackRoomBot(
                    self.sc,
                    bot_id=event.get('bot_id'),
                    bot_username=event.get('username', ''),
                    channelid=channel,
                    bot=self
                )
            else:
                msg.frm = SlackRoomOccupant(self.sc, event['user'], channel, bot=self)
            msg.to = SlackRoom(webclient=self.sc, channelid=channel, bot=self)
            channel_link_name = msg.to.name

        # TODO: port to slackclient2
        # msg.extras['url'] = f'https://{self.sc.server.domain}.slack.com/archives/' \
        #                     f'{channel_link_name}/p{self._ts_for_message(msg).replace(".", "")}'

        self.callback_message(msg)

        if mentioned:
            self.callback_mention(msg, mentioned)

    def _member_joined_channel_event_handler(self, raw_event):
        """Event handler for the 'member_joined_channel' event"""
        log.debug('Saw an event: %s', pprint.pformat(raw_event))
        event = raw_event['event']
        user = SlackPerson(self.sc, event['user'])
        if user == self.bot_identifier:
            self.callback_room_joined(SlackRoom(webclient=self.sc, channelid=event['channel'], bot=self))

    @staticmethod
    def userid_to_username(webclient: WebClient, id_: str):
        """Convert a Slack user ID to their user name"""
        user = webclient.users_info(user=id_)['user']
        if user is None:
            raise UserDoesNotExistError(f'Cannot find user with ID {id_}.')
        return user['name']

    @staticmethod
    def username_to_userid(webclient: WebClient, name: str):
        """Convert a Slack user name to their user ID"""
        name = name.lstrip('@')
        user = [user for user in webclient.users_list()['users'] if user['name'] == name]
        if user is None:
            raise UserDoesNotExistError(f'Cannot find user {name}.')
        return user['id']

    def channelid_to_channelname(self, id_: str):
        """Convert a Slack channel ID to its channel name"""
        channel = self.webclient.conversations_info(channel=id_)['channel']
        if channel is None:
            raise RoomDoesNotExistError(f'No channel with ID {id_} exists.')
        return channel['name']

    def channelname_to_channelid(self, name: str):
        """Convert a Slack channel name to its channel ID"""
        name = name.lstrip('#')
        channel = [channel for channel in self.webclient.channels_list() if channel.name == name]
        if not channel:
            raise RoomDoesNotExistError(f'No channel named {name} exists')
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
        response = self.webclient.channels_list(exclude_archived=exclude_archived)
        channels = [channel for channel in response['channels']
                    if channel['is_member'] or not joined_only]

        response = self.webclient.groups_list(exclude_archived=exclude_archived)
        # No need to filter for 'is_member' in this next call (it doesn't
        # (even exist) because leaving a group means you have to get invited
        # back again by somebody else.
        groups = [group for group in response['groups']]

        return channels + groups

    @lru_cache(1024)
    def get_im_channel(self, id_):
        """Open a direct message channel to a user"""
        try:
            response = self.webclient.im_open(user=id_)
            return response['channel']['id']
        except SlackAPIResponseError as e:
            if e.error == "cannot_dm_bot":
                log.info('Tried to DM a bot.')
                return None
            else:
                raise e

    def _prepare_message(self, msg):  # or card
        """
        Translates the common part of messaging for Slack.
        :param msg: the message you want to extract the Slack concept from.
        :return: a tuple to user human readable, the channel id
        """
        if msg.is_group:
            to_channel_id = msg.to.id
            to_humanreadable = msg.to.name if msg.to.name else self.channelid_to_channelname(to_channel_id)
        else:
            to_humanreadable = msg.to.username
            to_channel_id = msg.to.channelid
            if to_channel_id.startswith('C'):
                log.debug("This is a divert to private message, sending it directly to the user.")
                to_channel_id = self.get_im_channel(self.username_to_userid(msg.to.username))
        return to_humanreadable, to_channel_id

    def send_message(self, msg):
        super().send_message(msg)

        if msg.parent is not None:
            # we are asked to reply to a specify thread.
            try:
                msg.extras['thread_ts'] = self._ts_for_message(msg.parent)
            except KeyError:
                # Gives to the user a more interesting explanation if we cannot find a ts from the parent.
                log.exception('The provided parent message is not a Slack message '
                              'or does not contain a Slack timestamp.')

        to_humanreadable = "<unknown>"
        try:
            if msg.is_group:
                to_channel_id = msg.to.id
                to_humanreadable = msg.to.name if msg.to.name else self.channelid_to_channelname(to_channel_id)
            else:
                to_humanreadable = msg.to.username
                if isinstance(msg.to, RoomOccupant):  # private to a room occupant -> this is a divert to private !
                    log.debug("This is a divert to private message, sending it directly to the user.")
                    to_channel_id = self.get_im_channel(self.username_to_userid(msg.to.username))
                else:
                    to_channel_id = msg.to.channelid

            msgtype = "direct" if msg.is_direct else "channel"
            log.debug('Sending %s message to %s (%s).', msgtype, to_humanreadable, to_channel_id)
            body = self.md.convert(msg.body)
            log.debug('Message size: %d.', len(body))

            limit = min(self.bot_config.MESSAGE_SIZE_LIMIT, SLACK_MESSAGE_LIMIT)
            parts = self.prepare_message_body(body, limit)

            timestamps = []
            for part in parts:
                data = {
                    'channel': to_channel_id,
                    'text': part,
                    'unfurl_media': 'true',
                    'link_names': '1',
                    'as_user': 'true',
                }

                # Keep the thread_ts to answer to the same thread.
                if 'thread_ts' in msg.extras:
                    data['thread_ts'] = msg.extras['thread_ts']

                result = self.webclient.chat_postMessage(**data)
                timestamps.append(result['ts'])

            msg.extras['ts'] = timestamps
        except Exception:
            log.exception(f'An exception occurred while trying to send the following message '
                          f'to {to_humanreadable}: {msg.body}.')

    def _slack_upload(self, stream: Stream) -> None:
        """
        Performs an upload defined in a stream
        :param stream: Stream object
        :return: None
        """
        try:
            stream.accept()
            resp = self.webclient.files_upload(channels=stream.identifier.channelid,
                                               filename=stream.name,
                                               file=stream)
            if 'ok' in resp and resp['ok']:
                stream.success()
            else:
                stream.error()
        except Exception:
            log.exception(f'Upload of {stream.name} to {stream.identifier.channelname} failed.')

    def send_stream_request(self,
                            user: Identifier,
                            fsource: BinaryIO,
                            name: str = None,
                            size: int = None,
                            stream_type: str = None) -> Stream:
        """
            Starts a file transfer. For Slack, the size and stream_type are unsupported

            :param user: is the identifier of the person you want to send it to.
            :param fsource: is a file object you want to send.
            :param name: is an optional filename for it.
            :param size: not supported in Slack backend
            :param stream_type: not supported in Slack backend

            :return Stream: object on which you can monitor the progress of it.
        """
        stream = Stream(user, fsource, name, size, stream_type)
        log.debug('Requesting upload of %s to %s (size hint: %d, stream type: %s).',
                  name, user.channelname, size, stream_type)
        self.thread_pool.apply_async(self._slack_upload, (stream,))
        return stream

    def send_card(self, card: Card):
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

        if card.color:
            attachment['color'] = COLORS[card.color] if card.color in COLORS else card.color

        if card.fields:
            attachment['fields'] = [{'title': key, 'value': value, 'short': True} for key, value in card.fields]

        limit = min(self.bot_config.MESSAGE_SIZE_LIMIT, SLACK_MESSAGE_LIMIT)
        parts = self.prepare_message_body(card.body, limit)
        part_count = len(parts)
        footer = attachment.get('footer', '')
        for i in range(part_count):
            if part_count > 1:
                attachment['footer'] = f'{footer} [{i + 1}/{part_count}]'
            attachment['text'] = parts[i]
            data = {
                'channel': to_channel_id,
                'attachments': json.dumps([attachment]),
                'link_names': '1',
                'as_user': 'true'
            }
            try:
                log.debug('Sending data:\n%s', data)
                self.webclient.chat_postMessage(**data)
            except Exception:
                log.exception(f'An exception occurred while trying to send a card to {to_humanreadable}.[{card}]')

    def __hash__(self):
        return 0  # this is a singleton anyway

    def change_presence(self, status: str = ONLINE, message: str = '') -> None:
        self.webclient.users_setPresence(presence='auto' if status == ONLINE else 'away')

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
            <@U12345|user>
            @user
            #channel/user
            #channel

        Returns the tuple (username, userid, channelname, channelid).
        Some elements may come back as None.
        """
        exception_message = (
            'Unparseable slack identifier, should be of the format `<#C12345>`, `<@U12345>`, '
            '`<@U12345|user>`, `@user`, `#channel/user` or `#channel`. (Got `%s`)'
        )
        text = text.strip()

        if text == '':
            raise ValueError(exception_message % '')

        channelname = None
        username = None
        channelid = None
        userid = None

        if text[0] == '<' and text[-1] == '>':
            exception_message = 'Unparseable slack ID, should start with U, B, C, G, D or W (got `%s`)'
            text = text[2:-1]
            if text == '':
                raise ValueError(exception_message % '')
            if text[0] in ('U', 'B', 'W'):
                if '|' in text:
                    userid, username = text.split('|')
                else:
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
        log.debug('building an identifier from %s.', txtrep)
        username, userid, channelname, channelid = self.extract_identifiers_from_string(txtrep)

        if userid is None and username is not None:
            userid = self.username_to_userid(username)
        if channelid is None and channelname is not None:
            channelid = self.channelname_to_channelid(channelname)
        if userid is not None and channelid is not None:
            return SlackRoomOccupant(self.webclient, userid, channelid, bot=self)
        if userid is not None:
            return SlackPerson(self.webclient, userid, self.get_im_channel(userid))
        if channelid is not None:
            return SlackRoom(webclient=self.webclient, channelid=channelid, bot=self)

        raise Exception(
            "You found a bug. I expected at least one of userid, channelid, username or channelname "
            "to be resolved but none of them were. This shouldn't happen so, please file a bug."
        )

    def is_from_self(self, msg: Message) -> bool:
        return self.bot_identifier.userid == msg.frm.userid

    def build_reply(self, msg, text=None, private=False, threaded=False):
        response = self.build_message(text)

        if 'thread_ts' in msg.extras['slack_event']:
            # If we reply to a threaded message, keep it in the thread.
            response.extras['thread_ts'] = msg.extras['slack_event']['thread_ts']
        elif threaded:
            # otherwise check if we should start a new thread
            response.parent = msg

        response.frm = self.bot_identifier
        if private:
            response.to = msg.frm
        else:
            response.to = msg.frm.room if isinstance(msg.frm, RoomOccupant) else msg.frm
        return response

    def add_reaction(self, msg: Message, reaction: str) -> None:
        """
        Add the specified reaction to the Message if you haven't already.
        :param msg: A Message.
        :param reaction: A str giving an emoji, without colons before and after.
        :raises: ValueError if the emoji doesn't exist.
        """
        return self._react('reactions.add', msg, reaction)

    def remove_reaction(self, msg: Message, reaction: str) -> None:
        """
        Remove the specified reaction from the Message if it is currently there.
        :param msg: A Message.
        :param reaction: A str giving an emoji, without colons before and after.
        :raises: ValueError if the emoji doesn't exist.
        """
        return self._react('reactions.remove', msg, reaction)

    def _react(self, method: str, msg: Message, reaction: str) -> None:
        try:
            # this logic is from send_message
            if msg.is_group:
                to_channel_id = msg.to.id
            else:
                to_channel_id = msg.to.channelid

            ts = self._ts_for_message(msg)

            self.api_call(method, data={'channel': to_channel_id,
                                        'timestamp': ts,
                                        'name': reaction})
        except SlackAPIResponseError as e:
            if e.error == 'invalid_name':
                raise ValueError(e.error, 'No such emoji', reaction)
            elif e.error in ('no_reaction', 'already_reacted'):
                # This is common if a message was edited after you reacted to it, and you reacted to it again.
                # Chances are you don't care about this. If you do, call api_call() directly.
                pass
            else:
                raise SlackAPIResponseError(error=e.error)

    def _ts_for_message(self, msg):
        try:
            return msg.extras['slack_event']['message']['ts']
        except KeyError:
            return msg.extras['slack_event']['ts']

    def shutdown(self):
        super().shutdown()

    @property
    def mode(self):
        return 'slack'

    def query_room(self, room):
        """ Room can either be a name or a channelid """
        if room.startswith('C') or room.startswith('G'):
            return SlackRoom(webclient=self.webclient, channelid=room, bot=self)

        m = SLACK_CLIENT_CHANNEL_HYPERLINK.match(room)
        if m is not None:
            return SlackRoom(webclient=self.webclient, channelid=m.groupdict()['id'], bot=self)

        return SlackRoom(webclient=self.webclient, name=room, bot=self)

    def rooms(self):
        """
        Return a list of rooms the bot is currently in.

        :returns:
            A list of :class:`~SlackRoom` instances.
        """
        channels = self.channels(joined_only=True, exclude_archived=True)
        return [SlackRoom(webclient=self.webclient, channelid=channel['id'], bot=self) for channel in channels]

    def prefix_groupchat_reply(self, message, identifier):
        super().prefix_groupchat_reply(message, identifier)
        message.body = f'@{identifier.nick}: {message.body}'

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
        text = re.sub(r'<([^|>]+)\|([^|>]+)>', r'\2', text)
        text = re.sub(r'<(http([^>]+))>', r'\1', text)

        return text

    def process_mentions(self, text):
        """
        Process mentions in a given string
        :returns:
            A formatted string of the original message
            and a list of :class:`~SlackPerson` instances.
        """
        mentioned = []

        m = re.findall('<@[^>]*>*', text)

        for word in m:
            try:
                identifier = self.build_identifier(word)
            except Exception as e:
                log.debug("Tried to build an identifier from '%s' but got exception: %s", word, e)
                continue

            # We only track mentions of persons.
            if isinstance(identifier, SlackPerson):
                log.debug('Someone mentioned')
                mentioned.append(identifier)
                text = text.replace(word, str(identifier))

        return text, mentioned

