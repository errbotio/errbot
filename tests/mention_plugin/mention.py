from errbot import BotPlugin


class MentionTestPlugin(BotPlugin):
    def callback_mention(self, msg, people):
        if self.bot_identifier in people:
            self.send(msg.frm, "Somebody mentioned me!", msg)
            return
        self.send(
            msg.frm, "Somebody mentioned %s!" % ",".join(p.person for p in people), msg
        )
