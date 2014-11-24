import logging
import sys
import config
from errbot.backends.base import Message, build_message, Identifier, Presence, ONLINE, OFFLINE
from errbot.errBot import ErrBot

ENCODING_INPUT = sys.stdin.encoding
ANSI = hasattr(sys.stderr, 'isatty') and sys.stderr.isatty()
A_RESET = '\x1b[0m'
A_CYAN = '\x1b[36m'
A_BLUE = '\x1b[34m'


class TextBackend(ErrBot):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.jid = Identifier('Err')

    def serve_forever(self):
        me = Identifier(config.BOT_ADMINS[0])
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

    def join_room(self, room, username=None, password=None):
        pass  # just ignore that

    @property
    def mode(self):
        return 'text'
