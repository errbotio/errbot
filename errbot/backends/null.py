import logging
from time import sleep
from errbot.backends.base import Message, build_text_html_message_pair
from errbot.backends.text import SimpleIdentifier
from errbot.errBot import ErrBot

log = logging.getLogger(__name__)


class ConnectionMock():
    def send(self, mess):
        pass

    def send_message(self, mess):
        pass


class NullBackend(ErrBot):
    conn = ConnectionMock()
    running = True

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.jid = SimpleIdentifier('Err')  # whatever

    def serve_forever(self):
        self.connect()  # be sure we are "connected" before the first command
        self.connect_callback()  # notify that the connection occured
        try:
            while self.running:
                sleep(1)

        except EOFError:
            pass
        except KeyboardInterrupt:
            pass
        finally:
            log.debug("Trigger disconnect callback")
            self.disconnect_callback()
            log.debug("Trigger shutdown")
            self.shutdown()

    def connect(self):
        if not self.conn:
            self.conn = ConnectionMock()
        return self.conn

    def build_message(self, text):
        text, html = build_text_html_message_pair(text)
        return Message(text, html=html)

    def build_identifier(self, strrep):
        return SimpleIdentifier(strrep)

    def join_room(self, room, username=None, password=None):
        pass  # just ignore that

    def shutdown(self):
        if self.running:
            self.running = False
            super(NullBackend, self).shutdown()  # only once (hackish)

    @property
    def mode(self):
        return 'null'
