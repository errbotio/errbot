from errbot import BotPlugin, botcmd


class Parent2(BotPlugin):
    @botcmd
    def parent2_to_parent1(self, msg, args):
        return self.get_plugin("Parent1").shared_function()
