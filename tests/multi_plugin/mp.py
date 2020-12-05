from errbot import BotPlugin, botcmd


class WhateverName(BotPlugin):
    """Test plugin to verify that now class names don't matter."""

    @botcmd
    def myname(self, msg, args):
        return self.name
