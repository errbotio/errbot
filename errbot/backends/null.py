import logging
from time import sleep
from errbot.backends.base import Message
from errbot.errBot import ErrBot

class ConnectionMock():
    def send(self, mess):
        pass
    def send_message(self, mess):
        pass


class NullBackend(ErrBot):
    conn = ConnectionMock()
    running = True

    def serve_forever(self):
        self.jid = 'Err@localhost' # whatever
        self.connect() # be sure we are "connected" before the first command
        self.connect_callback() # notify that the connection occured
        try:
            while self.running:
                sleep(1)

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
        text, html = self.build_text_html_message_pair(text)
        return Message(text, html=html)

    def join_room(self, room, username=None, password=None):
        pass # just ignore that

    def shutdown(self):
        if self.running:
            self.running = False
            super(NullBackend, self).shutdown() # only once (hackish)

    @property
    def mode(self):
        return 'null'
