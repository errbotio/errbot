from errbot import BotPlugin, botcmd


class Parent1(BotPlugin):
    @botcmd
    def parent1_to_child1(self, msg, args):
        return self.get_plugin("Child1").shared_function()

    @botcmd
    def parent1_to_child2(self, msg, args):
        return self.get_plugin("Child2").shared_function()

    def shared_function(self):
        return "Hello from Parent1"
