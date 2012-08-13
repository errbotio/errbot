import logging
import sys
from errbot.backends.base import Backend, Identifier, Message

class ConnectionMock():
    def send(self, mess):
        print mess.getBody()

ENCODING_INPUT = sys.stdin.encoding

class TextBackend(Backend):
    conn = ConnectionMock()

    def serve_forever(self, connect_callback=None, disconnect_callback=None):
        self.jid = Identifier('blah') # whatever
        self.connect() # be sure we are "connected" before the first command
        if connect_callback:
            connect_callback()
        try:
            while True:
                entry = raw_input("Talk to  me >>").decode(ENCODING_INPUT)
                self.callback_message(self.conn, Message(entry))
        except EOFError as eof:
            pass
        except KeyboardInterrupt as ki:
            pass
        finally:
            if disconnect_callback:
                disconnect_callback()
            self.shutdown()

    def connect(self):
        if not self.conn:
            self.conn = ConnectionMock()
            self.activate_non_started_plugins()
            logging.info('Notifying connection to all the plugins...')
            self.signal_connect_to_all_plugins()
            logging.info('Plugin activation done.')
        return self.conn

    def build_message(self, text):
        return Message(text)

    def shutdown(self):
        pass

