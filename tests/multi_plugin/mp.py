from __future__ import absolute_import
from errbot import BotPlugin, botcmd


class WhateverName(BotPlugin):
    """Test plugin to verify that now class names don't matter.
    """
    @botcmd
    def name(self, msg, args):
        return self.name
