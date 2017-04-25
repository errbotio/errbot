from errbot import BotPlugin, botmatch


class MatchAll(BotPlugin):
    @botmatch(r".*")
    def all(self, msg, match):
        return 'Works!'
