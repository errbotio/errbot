import json
import logging
import time
import sys
from errbot.backends.base import Message, build_message, Identifier, Presence, ONLINE, OFFLINE, MUCRoom, MUCOccupant
from errbot.errBot import ErrBot
from errbot.utils import deprecated

try:
    from slackclient import SlackClient
except ImportError:
    # TODO make that properly
    logging.Error("SlackClient needs to be installed : pip install slackclient")
    raise

def api_resp(b):
    return json.loads(b.decode('utf-8'))

class SlackBackend(ErrBot):

    def __init__(self, config):
        super().__init__(config)
        identity = config.BOT_IDENTITY
        self.token = identity.get('token', None)
        if not self.token:
            # TODO make that properly
            raise Exception('You need a slack token from the "Bot Integration"')
        self.sc = SlackClient(self.token)
        self.auth = api_resp(self.sc.api_call("auth.test"))
        self.jid = Identifier(node=self.auth["user_id"], resource=self.auth["user_id"])


    def serve_forever(self):
        if self.sc.rtm_connect():
            try:
                while True:
                    events = self.sc.rtm_read()
                    for event in events:
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
                                status = OFFLINE # TODO: all the cases

                            self.callback_presence(Presence(identifier=idd, status=status))
                        elif t == 'message':
                            channel = event['channel']
                            channel_info = api_resp(self.sc.api_call("channels.info", channel=channel))
                            logging.debug('Slack channel: {}'.format(channel_info))
                            is_channel = channel_info['channel']['is_channel']
                            msg = Message(event['text'], type_= 'groupchat' if is_channel else 'chat')
                            msg.frm = Identifier(node=event['channel'], resource=event['user'])
                            msg.to = Identifier(node=event['channel'], resource=self.jid.node)
                            self.callback_message(msg)

                    time.sleep(1)
            finally:
                logging.debug("Trigger disconnect callback")
                self.disconnect_callback()
                logging.debug("Trigger shutdown")
                self.shutdown()

        else:
            raise Exception('Connection failed, invalid token ?')

    def send_message(self, mess):
        super().send_message(mess)
        logging.debug("trying to send to node %s" % mess.to.node)
        logging.debug("trying to send to resource %s" % mess.to.resource)
        logging.debug("trying to type %s" % mess.type)
        if mess.type == 'groupchat':
            logging.debug('send grouchat message to %s' % mess.to.resource)
            self.sc.rtm_send_message(mess.to.node, mess.body)
        else:
            logging.debug('send chat message to %s' % mess.to.resource)
            self.sc.rtm_send_message(mess.to.node, mess.body)


    def build_message(self, text):
        return build_message(text, Message)

    def build_reply(self, mess, text=None, private=False):
        return super(SlackBackend, self).build_reply(mess, text, False)


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
