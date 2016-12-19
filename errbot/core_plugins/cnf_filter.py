from errbot import BotPlugin, cmdfilter


class CommandNotFoundFilter(BotPlugin):
    """
    Allow overriding behavior when a command is not found.
    Attribute "catch_unprocessed" causes filter to be executed when a command
    is not found.
    """
    def __init__(self, *args, **kwargs):
        super(CommandNotFoundFilter, self).__init__(*args, **kwargs)
        self.catch_unprocessed = True

    @cmdfilter
    def cnf_filter(self, msg, cmd, args, dry_run, emptycmd=False):
        """
        Check if command exists.  If not, signal plugins.  This plugin
        will be called twice: once as a command filter and then again
        as a "command not found" filter. See the emptycmd parameter.

        :param msg: Original chat message.
        :param cmd: Parsed command.
        :param args: Command arguments.
        :param dry_run: True when this is a dry-run.
        :param emptycmd: False when this command has been parsed and is valid.
        True if the command was not found.
        """

        if not emptycmd:
            return msg, cmd, args

        if self._bot.bot_config.SUPPRESS_CMD_NOT_FOUND:
            log.debug("Surpressing command not found feedback")
        else:
            if msg.body.find(' ') > 0:
                command = msg.body[:msg.body.index(' ')]
            else:
                command = msg.body

            reply = self._bot.unknown_command(msg, command, args)
            if reply is None:
                reply = self.MSG_UNKNOWN_COMMAND % {'command': cmd}
            if reply:
                return reply
