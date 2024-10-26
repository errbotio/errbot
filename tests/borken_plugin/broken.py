from errbot import BotPlugin, botcmd

import borken  # fails on purpose # noqa: F401

class Broken(BotPlugin):
    @botcmd
    def hello(self, msg, args):
        """this command says hello"""
        return "Hello World !"
