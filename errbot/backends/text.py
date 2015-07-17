# vim: ts=4:sw=4
import logging
import sys
from ansi.color import fg, bg, fx
from errbot.rendering import ansi, text
from errbot.backends import SimpleIdentifier
from errbot.backends.base import Message, Presence, ONLINE, OFFLINE, MUCRoom
from errbot.errBot import ErrBot
from errbot.utils import deprecated
log = logging.getLogger(__name__)

ENCODING_INPUT = sys.stdin.encoding
ANSI = hasattr(sys.stderr, 'isatty') and sys.stderr.isatty()


class TextBackend(ErrBot):

    def __init__(self, config):
        super().__init__(config)
        log.debug("Text Backend Init.")
        self.bot_identifier = self.build_identifier('Err')
        self.rooms = set()
        self.md = ansi() if ANSI else text()

    def serve_forever(self):
        me = self.build_identifier(self.bot_config.BOT_ADMINS[0])
        self.connect_callback()  # notify that the connection occured
        self.callback_presence(Presence(identifier=me, status=ONLINE))
        try:
            while True:
                if ANSI:
                    entry = input('\n' + str(fg.cyan) + ' >>> ' + str(fx.reset))
                else:
                    entry = input('\n>>> ')
                msg = Message(entry)
                msg.frm = me
                msg.to = self.bot_identifier
                self.callback_message(msg)
        except EOFError:
            pass
        except KeyboardInterrupt:
            pass
        finally:
            # simulate some real presence
            self.callback_presence(Presence(identifier=me, status=OFFLINE))
            log.debug("Trigger disconnect callback")
            self.disconnect_callback()
            log.debug("Trigger shutdown")
            self.shutdown()

    def send_message(self, mess):
        super(TextBackend, self).send_message(mess)
        print('\n\n' + self.md.convert(mess.body) + '\n\n')

    def build_identifier(self, text_representation):
        return SimpleIdentifier(text_representation)

    def build_reply(self, mess, text=None, private=False):
        response = self.build_message(text)
        response.frm = self.bot_identifier
        response.to = mess.frm
        response.type = 'chat' if private else mess.type
        return response

    def shutdown(self):
        super(TextBackend, self).shutdown()

    @deprecated
    def join_room(self, room, username=None, password=None):
        return self.query_room(room)

    @property
    def mode(self):
        return 'text'

    def query_room(self, room):
        room = TextMUCRoom()
        self.rooms.add(room)
        return room

    def rooms(self):
        return self.rooms

    def groupchat_reply_format(self):
        return '{0} {1}'


class TextMUCRoom(MUCRoom):

    def __init__(self):
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
        return [self.build_identifier("Somebody")]

    def invite(self, *args):
        pass
