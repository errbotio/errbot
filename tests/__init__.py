from Queue import Queue
import logging
from errbot.backends.base import Message
from errbot.errBot import ErrBot

incoming_message_queue = Queue()
outgoing_message_queue = Queue()

QUIT_MESSAGE = '$STOP$'

class ConnectionMock():
    def send(self, mess):
        outgoing_message_queue.put(mess.getBody())
    def send_message(self, mess):
        self.send(mess)

class TestBackend(ErrBot):
    conn = ConnectionMock()

    def serve_forever(self):
        import config
        self.jid = 'Err@localhost'  # whatever
        self.connect()  # be sure we are "connected" before the first command
        self.connect_callback()  # notify that the connection occured
        try:
            while True:
                entry = incoming_message_queue.get()
                if entry == QUIT_MESSAGE:
                    logging.info("Stop magic message received, quitting...")
                    break
                msg = Message(entry)
                msg.setFrom(config.BOT_ADMINS[0]) # assume this is the admin talking
                msg.setTo(self.jid) # To me only
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
        return Message(self.build_text_html_message_pair(text)[0])  # 0 = Only retain pure text

    def shutdown(self):
        super(TestBackend, self).shutdown()

    def join_room(self, room, username=None, password=None):
        pass  # just ignore that

    @property
    def mode(self):
        return 'text'
