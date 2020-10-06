from __future__ import absolute_import
from errbot import BotPlugin, botcmd


class FlowTest(BotPlugin):
    """A plugin to test the flows
    see flowtest.png for the structure.
    """

    @botcmd
    def a(self, msg, args):
        return "a"

    @botcmd
    def b(self, msg, args):
        return "b"

    @botcmd
    def c(self, msg, args):
        return "c"

    @botcmd(flow_only=True)
    def d(self, msg, args):
        return "d"

    @botcmd
    def e(self, msg, args):
        return "e"
