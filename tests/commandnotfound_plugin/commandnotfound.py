from errbot import BotPlugin, cmdfilter


class TestCommandNotFoundFilter(BotPlugin):
    def __init__(self, *args, **kwargs):
        super(TestCommandNotFoundFilter, self).__init__(*args, **kwargs)
        self.catch_unprocessed = True

    @cmdfilter
    def command_not_found(self, msg, cmd, args, dry_run, emptycmd=False):
        if not emptycmd:
            return msg, cmd, args

        return "Command fell through: {}".format(msg)
