from errbot import BotPlugin, botcmd


class DummyTest(BotPlugin):
    """Just a test plugin to see if it is picked up.
    """
    @botcmd
    def foo(self, msg, args):
        return 'bar'
