from __future__ import absolute_import
from errbot import BotPlugin, botcmd, re_botcmd


class FlowTest(BotPlugin):
    """A plugin to test the flows
    """
    @botcmd
    def foo(self, msg, args):
        """This runs foo."""
        return 'bar'

    @re_botcmd(pattern=r"plz dont match this")
    def re_foo(self, msg, match):
        """This runs re_foo."""
        return 'bar'
