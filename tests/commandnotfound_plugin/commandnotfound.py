from errbot import BotPlugin, cmdfilter


class TestCommandNotFoundFilter(BotPlugin):

    @cmdfilter(catch_unprocessed=True)
    def command_not_found(self, msg, cmd, args, dry_run, emptycmd=False):
        if not emptycmd:
            return msg, cmd, args

        return "Command fell through: {}".format(msg)
