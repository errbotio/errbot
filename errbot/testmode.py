import logging
import sys
import config

class JIDMock():
    domain = 'meuh'
    resource = 'bidon'

    def __init__(self, node):
        self.node = node
    def getNode(self):
        return self.node
    def bareMatch(self, whatever):
        return False
    def getStripped(self):
        return self.node

class MessageMock():
    def __init__(self, body):
        self.body = body
    def getType(self):
        return 'chat'
    def getFrom(self):
        return JIDMock(config.BOT_ADMINS[0])
    def getProperties(self):
        return {}
    def getBody(self):
        return self.body
    def getThread(self):
        return None

class ConnectionMock():
    def send(self, mess):
        if hasattr(mess, 'getBody'):
            print mess.getBody()

ENCODING_INPUT = sys.stdin.encoding

def patch_jabberbot():
    from errbot import jabberbot

    conn = ConnectionMock()

    def fake_serve_forever(self):
        self.jid = JIDMock('blah') # whatever
        self.connect() # be sure we are "connected" before the first command
        try:
            while True:
                entry = raw_input("Talk to  me >>").decode(ENCODING_INPUT)
                self.callback_message(conn, MessageMock(entry))
        except EOFError as eof:
            pass
        except KeyboardInterrupt as ki:
            pass
        finally:
            print "\nExiting..."

    def fake_connect(self):
        if not self.conn:
            self.conn = ConnectionMock()
            self.activate_non_started_plugins()
            logging.info('Notifying connection to all the plugins...')
            self.signal_connect_to_all_plugins()
            logging.info('Plugin activation done.')
        return self.conn

    jabberbot.JabberBot.serve_forever = fake_serve_forever
    jabberbot.JabberBot.connect = fake_connect