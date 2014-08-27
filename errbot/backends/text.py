import logging
import sys
import config
from errbot.backends.base import Message, build_message, Identifier, Presence, ONLINE, OFFLINE
from errbot.errBot import ErrBot


class ConnectionMock(object):
    def send(self, mess):
        print(mess.body)

    def send_message(self, mess):
        self.send(mess)


ENCODING_INPUT = sys.stdin.encoding


class TextBackend(ErrBot):
    conn = ConnectionMock()

    def serve_forever(self):
        self.jid = Identifier('Err')
        me = Identifier(config.BOT_ADMINS[0])
        self.connect()  # be sure we are "connected" before the first command
        self.connect_callback()  # notify that the connection occured
        self.callback_presence(self.conn, Presence(identifier=me, status=ONLINE))
        try:
            while True:
                entry = input("Talk to  me >>")
                msg = Message(entry)
                msg.frm = me
                msg.to = self.jid
                self.callback_message(self.conn, msg)
        except EOFError as eof:
            pass
        except KeyboardInterrupt as ki:
            pass
        finally:
            # simulate some real presence
            self.callback_presence(self.conn, Presence(identifier=me, status=OFFLINE))
            logging.debug("Trigger disconnect callback")
            self.disconnect_callback()
            logging.debug("Trigger shutdown")
            self.shutdown()

    def connect(self):
        if not self.conn:
            self.conn = ConnectionMock()
        return self.conn

    def build_message(self, text):
        return build_message(text, Message)

    def shutdown(self):
        super(TextBackend, self).shutdown()

    def join_room(self, room, username=None, password=None):
        pass  # just ignore that

    @property
    def mode(self):
        return 'text'
