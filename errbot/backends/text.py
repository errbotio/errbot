import logging
import sys
import config
from errbot.backends.base import Message, build_message
from errbot.errBot import ErrBot


class ConnectionMock(object):
    def send(self, mess):
        print mess.getBody()

    def send_message(self, mess):
        self.send(mess)


ENCODING_INPUT = sys.stdin.encoding


class TextBackend(ErrBot):
    conn = ConnectionMock()

    def serve_forever(self):
        self.jid = 'Err@localhost'  # whatever
        self.connect()  # be sure we are "connected" before the first command
        self.connect_callback()  # notify that the connection occured
        try:
            while True:
                entry = raw_input("Talk to  me >>").decode(ENCODING_INPUT)
                msg = Message(entry)
                msg.setFrom(config.BOT_ADMINS[0])  # assume this is the admin talking
                msg.setTo(self.jid)  # To me only
                self.callback_message(self.conn, msg)
        except EOFError as eof:
            pass
        except KeyboardInterrupt as ki:
            pass
        finally:
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
