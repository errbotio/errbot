from errbot import BotPlugin, cmdfilter


class CommandNotFoundFilter(BotPlugin):
    @cmdfilter(catch_unprocessed=True)
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

        if self.bot_config.SUPPRESS_CMD_NOT_FOUND:
            self.log.debug('Suppressing command not found feedback.')
            return

        command = msg.body.strip()

        for prefix in self.bot_config.BOT_ALT_PREFIXES + (self.bot_config.BOT_PREFIX,):
            if command.startswith(prefix):
                command = command.replace(prefix, '', 1)
                break

        command_args = command.split(' ', 1)
        command = command_args[0]
        if len(command_args) > 1:
            args = ' '.join(command_args[1:])

        return self._bot.unknown_command(msg, command, args)
