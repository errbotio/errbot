from errbot import BotPlugin, botcmd


class MentionTestPlugin(BotPlugin):
    def callback_mention(self, message, people):
        if self.bot_identifier in people:
            self.send(message.frm, "Somebody mentioned me!", message_type=message.type)
        else:
            self.send(message.frm, "Somebody mentioned %s!" %
                      ','.join(p.person for p in people), message_type=message.type)
