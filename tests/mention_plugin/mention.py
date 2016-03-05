from errbot import BotPlugin


class MentionTestPlugin(BotPlugin):
    def callback_mention(self, message, people):
        if self.bot_identifier in people:
            return "Somebody mentioned me!"
        return "Somebody mentioned %s!" % ','.join(p.person for p in people)
