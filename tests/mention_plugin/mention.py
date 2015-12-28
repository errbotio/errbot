# This is a skeleton for Err plugins, use this to get started quickly.

from errbot import BotPlugin, botcmd


class Skeleton(BotPlugin):
    """An Err plugin skeleton"""
    min_err_version = '1.6.0'  # Optional, but recommended
    max_err_version = '9.9.9'  # Optional, but recommended

    @botcmd
    def hello(self, msg, args):
        """Say hello to the world"""
        return "Hi, my name is %s" % self.bot_identifier.username

    def callback_mention(self, message, people):
        if self.bot_identifier.userid in (p.userid for p in people):
            self.send(message.frm, "Somebody mentioned me!", message_type=message.type)
        else:
            self.send(message.frm, "Somebody mentioned someone!", message_type=message.type)
