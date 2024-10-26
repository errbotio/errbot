from errbot import BotPlugin


class Child1(BotPlugin):
    def shared_function(self):
        return "Hello from Child1"
