from errbot import BotPlugin, botcmd
class TestCommandNotFound(BotPlugin):
    def callback_command_not_found(self, msg):
        self.send(msg.frm, "Command fell through: {}".format(msg))

