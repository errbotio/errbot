from errbot import BotPlugin, cmdfilter


class CommandNotFoundFilter(BotPlugin):
    """
    Allow overriding behavior when a command is not found.
    """
    def __init__(self, *args, **kwargs):
        super(CommandNotFoundFilter, self).__init__(*args, **kwargs)
        self.catch_unprocessed = True

    @cmdfilter
    def cnf_filter(self, msg, cmd, args, dry_run, emptycmd=False):
        """
        Check if command exists.  If not, signal plugins.

        :param msg: Original chat message.
        :param cmd: Parsed command.
        :param args: Command arguments.
        :param dry_run: True when this is a dry-run.
        """

        if not emptycmd:
            return msg, cmd, args

        return "Command '{}' not filtered.".format(msg)
