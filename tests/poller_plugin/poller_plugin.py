from __future__ import absolute_import
from errbot import BotPlugin, botcmd


class PollerPlugin(BotPlugin):

    def delayed_hello(self, frm):
        self.send(frm, 'Hello world! was sent 5 seconds ago')

    @botcmd
    def hello(self, msg, args):
        """Say hello to the world."""
        self.start_poller(0.1, self.delayed_hello, times=1,
                          kwargs={'frm': msg.frm})
        return "Hello, world!"
