import logging
import sys
from errbot.backends.base import Message, build_message, Identifier, Presence, ONLINE, OFFLINE, MUCRoom, MUCOccupant
from errbot.errBot import ErrBot
from errbot.utils import deprecated

ENCODING_INPUT = sys.stdin.encoding
ANSI = hasattr(sys.stderr, 'isatty') and sys.stderr.isatty()
A_RESET = '\x1b[0m'
A_CYAN = '\x1b[36m'
A_BLUE = '\x1b[34m'


class TextBackend(ErrBot):

    def __init__(self, config):
        super().__init__(config)
        self.jid = Identifier('Err')
        self.rooms = set()

    def serve_forever(self):
        me = Identifier(self.bot_config.BOT_ADMINS[0])
        self.connect_callback()  # notify that the connection occured
        self.callback_presence(Presence(identifier=me, status=ONLINE))
        try:
            while True:
                if ANSI:
                    entry = input('\n' + A_CYAN + ' >>> ' + A_RESET)
                else:
                    entry = input('\n>>> ')
                msg = Message(entry)
                msg.frm = me
                msg.to = self.jid
                self.callback_message(msg)
        except EOFError:
            pass
        except KeyboardInterrupt:
            pass
        finally:
            # simulate some real presence
            self.callback_presence(Presence(identifier=me, status=OFFLINE))
            logging.debug("Trigger disconnect callback")
            self.disconnect_callback()
            logging.debug("Trigger shutdown")
            self.shutdown()

    def send_message(self, mess):
        super(TextBackend, self).send_message(mess)
        if ANSI:
            print('\n\n' + A_BLUE + mess.body + A_RESET + '\n\n')
        else:
            print('\n\n' + mess.body + '\n\n')

    def build_message(self, text):
        return build_message(text, Message)

    def shutdown(self):
        super(TextBackend, self).shutdown()

    @deprecated
    def join_room(self, room, username=None, password=None):
        return self.query_room(room)

    @property
    def mode(self):
        return 'text'

    def query_room(self, room):
        room = TextMUCRoom(room)
        self.rooms.add(room)
        return room

    def rooms(self):
        return self.rooms


class TextMUCRoom(MUCRoom):
    def __init__(self, jid=None, node='', domain='', resource=''):
        super().__init__(jid, node, domain, resource)
        self.topic_ = ''
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
        return True

    @property
    def joined(self):
        return self.joined_

    @property
    def topic(self):
        return self.topic_

    @topic.setter
    def topic(self, topic):
        self.topic_ = topic

    @property
    def occupants(self):
        return [MUCOccupant("Somebody")]

    def invite(self, *args):
        pass
