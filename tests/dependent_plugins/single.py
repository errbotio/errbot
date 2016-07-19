from errbot import BotPlugin, botcmd


class Single(BotPlugin):

    @botcmd
    def depfunc(self, msg, args):
        return self.get_plugin('Parent1').shared_function()
