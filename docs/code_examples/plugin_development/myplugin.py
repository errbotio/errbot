from errbot import BotPlugin, botcmd

class MyPlugin(BotPlugin):
    @botcmd
    def mycommand(self, message, args):
        return self.mycommand_helper()

    @botcmd
    def mycommand_another(self, message, args):
        return self.mycommand_another_helper()

    @staticmethod
    def mycommand_helper():
        return "This is my awesome command"

    def mycommand_another_helper(self):
        return "This is another awesome command"
