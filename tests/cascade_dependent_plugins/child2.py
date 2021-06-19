from errbot import BotPlugin, botcmd


class Child2(BotPlugin):
    def shared_function(self):
        return "Hello from Child2"
