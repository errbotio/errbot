from errbot import BotPlugin, botcmd


class Child1(BotPlugin):
    def shared_function(self):
        return "Hello from Child1"
