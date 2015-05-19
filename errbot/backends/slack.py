import json
import logging
import time
import sys
from errbot import PY3
from errbot.backends.base import Message, build_message, Identifier, Presence, ONLINE, OFFLINE, MUCRoom, MUCOccupant
from errbot.errBot import ErrBot
from errbot.utils import deprecated

try:
    from slackclient import SlackClient
except ImportError:
    logging.exception("Could not start the Slack back-end")
    logging.fatal(
        "You need to install the slackclient package in order to use the Slack "
        "back-end. You should be able to install this package using: "
        "pip install slackclient"
    )
    sys.exit(1)
except SyntaxError:
    if not PY3:
        raise
    logging.exception("Could not start the Slack back-end")
    logging.fatal(
        "I cannot start the Slack back-end because I cannot import the SlackClient. "
        "Python 3 compatibility on SlackClient is still quite young, you may be "
        "running an old version or perhaps they released a version with a Python "
        "3 regression. As a last resort to fix this, you could try installing the "
        "latest master version from them using: "
        "pip install --upgrade https://github.com/slackhq/python-slackclient/archive/master.zip"
    )
    sys.exit(1)



def api_resp(b):
    return json.loads(b.decode('utf-8'))


class SlackBackend(ErrBot):

    def __init__(self, config):
        super().__init__(config)
        identity = config.BOT_IDENTITY
        self.token = identity.get('token', None)
        if not self.token:
            logging.fatal(
                'You need to set your token (found under "Bot Integration" on Slack) in '
                'the BOT_IDENTITY setting in your configuration. Without this token I '
                'cannot connect to Slack.'
            )
            sys.exit(1)
        self.sc = SlackClient(self.token)

        logging.debug("Verifying authentication token")
        self.auth = api_resp(self.sc.api_call("auth.test"))
        if not self.auth['ok']:
            logging.fatal("Couldn't authenticate with Slack. Server said: %s" % self.auth['error'])
            sys.exit(1)
        logging.debug("Token accepted")
        self.jid = Identifier(node=self.auth["user_id"], resource=self.auth["user_id"])

    def serve_forever(self):
        logging.info("Connecting to Slack real-time-messaging API")
        if self.sc.rtm_connect():
            logging.info("Connected")
            try:
                while True:
                    events = self.sc.rtm_read()
                    for event in events:
                        self._handle_slack_event(event)
                    time.sleep(1)
            except KeyboardInterrupt:
                logging.info("Caught KeyboardInterrupt, shutting down..")
            finally:
                logging.debug("Trigger disconnect callback")
                self.disconnect_callback()
                logging.debug("Trigger shutdown")
                self.shutdown()

        else:
            raise Exception('Connection failed, invalid token ?')

    def _handle_slack_event(self, event):
        """
        Act on a Slack event from the RTM stream
        """
        logging.debug("Slack event: %s" % event)
        t = event.get('type', None)
        if t == 'hello':
            self.connect_callback()
            self.callback_presence(Presence(identifier=self.jid, status=ONLINE))
        elif t == 'presence_change':
            idd = Identifier(node=event['user'])
            sstatus = event['presence']
            if sstatus == 'active':
                status = ONLINE
            else:
                status = OFFLINE  # TODO: all the cases

            self.callback_presence(Presence(identifier=idd, status=status))
        elif t == 'message':
            channel = event['channel']
            if channel.startswith('C'):
                logging.debug("Handling message from a public channel")
                message_type = 'groupchat'
            elif channel.startswith('G'):
                logging.debug("Handling message from a private group")
                message_type = 'groupchat'
            elif channel.startswith('D'):
                logging.debug("Handling message from a user")
                message_type = 'chat'
            else:
                logging.warning("Unknown message type! Unable to handle")
                return

            msg = Message(event['text'], type_=message_type)
            msg.frm = Identifier(
                node=self.userid_to_username(event['user']),
                domain=self.channelid_to_channelname(event['channel'])
            )
            msg.to = Identifier(
                node=self.sc.server.username,
                domain=self.channelid_to_channelname(event['channel'])
            )
            self.callback_message(msg)

    def userid_to_username(self, id):
        """Convert a Slack user ID to their user name"""
        return self.sc.server.users.find(id).name

    def username_to_userid(self, name):
        """Convert a Slack user name to their user ID"""
        return self.sc.server.users.find(name).id

    def channelid_to_channelname(self, id):
        """Convert a Slack channel ID to its channel name"""
        return self.sc.server.channels.find(id).name

    def channelname_to_channelid(self, name):
        """Convert a Slack channel name to its channel ID"""
        return self.sc.server.channels.find(name).id

    def send_message(self, mess):
        super().send_message(mess)
        to_humanreadable = "<unknown>"
        try:
            if mess.type == 'groupchat':
                to_humanreadable = mess.to.domain
                to_id = self.channelname_to_channelid(to_humanreadable)
            else:
                to_humanreadable = mess.to.node
                api_data = api_resp(
                    self.sc.api_call(
                        'im.open',
                        user=self.username_to_userid(to_humanreadable)
                    )
                )
                if not api_data['ok']:
                    raise RuntimeError("Couldn't open direct message channel with user")
                to_id = api_data['channel']['id']

            logging.debug('Sending %s message to %s (%s)' % (mess.type, to_humanreadable, to_id))
            self.sc.rtm_send_message(to_id, mess.body)
        except Exception:
            logging.exception(
                "An exception occurred while trying to send the following message "
                "to %s: %s" % (to_humanreadable, mess.body)
            )

    def build_message(self, text):
        return build_message(text, Message)

    def build_reply(self, mess, text=None, private=False):
        msg_type = mess.type
        response = self.build_message(text)

        response.frm = self.jid
        if msg_type == "groupchat" and private:
            response.to = mess.frm.node
        else:
            response.to = mess.frm
        response.type = 'chat' if private else msg_type

        return response

    def shutdown(self):
        super().shutdown()

    @deprecated
    def join_room(self, room, username=None, password=None):
        return self.query_room(room)

    @property
    def mode(self):
        return 'slack'

    def query_room(self, room):
        return SlackRoom(node=room, sc=self.sc)

    def groupchat_reply_format(self):
        return '{0} {1}'


class SlackRoom(MUCRoom):
    def __init__(self, jid=None, node='', domain='', resource='', sc=None):
        super().__init__(jid, node, domain, resource)
        self.channel = sc.server.channels.find(node)
        self.joined_ = False

    def join(self, username=None, password=None):
        self.joined_ = True

    def leave(self, reason=None):
        self.joined_ = False

    def create(self):
        self.joined_ = True

    def destroy(self):
        self.joined_ = False

    @property
    def exists(self):
        return self.channel

    @property
    def joined(self):
        return self.joined_

    @property
    def topic(self):
        return "TODO"

    @topic.setter
    def topic(self, topic):
        self.topic_ = topic

    @property
    def occupants(self):
        return [MUCOccupant("Somebody")]

    def invite(self, *args):
        pass
