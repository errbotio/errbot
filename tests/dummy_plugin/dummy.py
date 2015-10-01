from __future__ import absolute_import
from errbot import BotPlugin, botcmd, re_botcmd


class DummyTest(BotPlugin):
    """Just a test plugin to see if it is picked up.
    """
    @botcmd
    def foo(self, msg, args):
        """This runs foo."""
        return 'bar'

    @re_botcmd(pattern=ur"plz dont match this")
    def re_foo(self, msg, match):
        """This runs re_foo."""
        return 'bar'
