import borken  # fails on purpose
from errbot import BotPlugin, botcmd


class Broken(BotPlugin):

    @botcmd
    def hello(self, msg, args):
        """ this command says hello """
        return "Hello World !"
