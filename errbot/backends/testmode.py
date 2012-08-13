import logging
import sys
from errbot.backends.base import Identifier, Message
from errbot.errBot import ErrBot

class ConnectionMock():
    def send(self, mess):
        print mess.getBody()

ENCODING_INPUT = sys.stdin.encoding

class TextBackend(ErrBot):
    conn = ConnectionMock()

    def serve_forever(self):
        self.jid = Identifier('blah') # whatever
        self.connect() # be sure we are "connected" before the first command
        self.connect_callback() # notify that the connection occured
        try:
            while True:
                entry = raw_input("Talk to  me >>").decode(ENCODING_INPUT)
                self.callback_message(self.conn, Message(entry))
        except EOFError as eof:
            pass
        except KeyboardInterrupt as ki:
            pass
        finally:
            self.disconnect_callback()
            self.shutdown()

    def connect(self):
        if not self.conn:
            self.conn = ConnectionMock()
        return self.conn

    def build_message(self, text):
        return Message(text)

    def shutdown(self):
        super(TextBackend, self).shutdown()

