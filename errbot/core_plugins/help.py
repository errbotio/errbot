from errbot import BotPlugin, botcmd
from errbot.version import VERSION
from errbot.utils import get_class_that_defined_method


class Help(BotPlugin):
    min_err_version = VERSION  # don't copy paste that for your plugin, it is just because it is a bundled plugin !
    max_err_version = VERSION

    MSG_HELP_TAIL = 'Type help <command name> to get more info ' \
                    'about that specific command.'
    MSG_HELP_UNDEFINED_COMMAND = 'That command is not defined.'

    # noinspection PyUnusedLocal
    @botcmd
    def about(self, mess, args):
        """ Returns some information about this err instance"""

        result = 'Err version %s \n\n' % VERSION
        result += ('Authors: Mondial Telecom, Guillaume BINET, Tali PETROVER, '
                   'Ben VAN DAELE, Paul LABEDAN and others.\n\n')
        return result

    # noinspection PyUnusedLocal
    @botcmd
    def apropos(self, mess, args):
        """   Returns a help string listing available options.

        Automatically assigned to the "help" command."""
        if not args:
            return 'Usage: ' + self._bot.prefix + 'apropos search_term'

        description = 'Available commands:\n'

        clazz_commands = {}
        for (name, command) in self._bot.commands.items():
            clazz = get_class_that_defined_method(command)
            clazz = str.__module__ + '.' + clazz.__name__  # makes the fuul qualified name
            commands = clazz_commands.get(clazz, [])
            if not self.bot_config.HIDE_RESTRICTED_COMMANDS or self._bot.check_command_access(mess, name)[0]:
                commands.append((name, command))
                clazz_commands[clazz] = commands

        usage = ''
        for clazz in sorted(clazz_commands):
            usage += '\n'.join(sorted([
                '\t' + self._bot.prefix + '%s: %s' % (
                    name.replace('_', ' ', 1),
                    (command.__doc__ or '(undocumented)').strip().split('\n', 1)[0]
                )
                for (name, command) in clazz_commands[clazz]
                if args is not None and
                command.__doc__ is not None and
                args.lower() in command.__doc__.lower() and
                name != 'help' and not command._err_command_hidden
            ]))
        usage += '\n\n'

        top = self._bot.top_of_help_message()
        bottom = self._bot.bottom_of_help_message()
        return ''.join(filter(None, [top, description, usage, bottom])).strip()

    @botcmd
    def help(self, mess, args):
        """   Returns a help string listing available options.

        Automatically assigned to the "help" command."""

        def may_access_command(cmd):
            try:
                self._bot.check_command_access(mess, cmd)
                return True
            except ACLViolation:
                return False

        usage = ''
        if not args:
            description = '### Available help\n\n'
            command_classes = sorted(set(self._bot.get_command_classes()), key=lambda c: c.__name__)
            usage = '\n'.join(
                '- **' + self._bot.prefix + 'help %s** \- %s' %
                (clazz.__name__, clazz.__errdoc__.strip() or '(undocumented)') for clazz in command_classes)
        elif args == 'full':
            description = '### Available commands\n\n'

            clazz_commands = {}
            for (name, command) in self._bot.commands.items():
                clazz = get_class_that_defined_method(command)
                commands = clazz_commands.get(clazz, [])
                if not self.bot_config.HIDE_RESTRICTED_COMMANDS or may_access_command(name):
                    commands.append((name, command))
                    clazz_commands[clazz] = commands

            for clazz in sorted(set(clazz_commands), key=lambda c: c.__name__):
                usage += '\n\n**%s** \- %s\n' % (clazz.__name__, clazz.__errdoc__ or '')
                usage += '\n'.join(sorted(['**' +
                                           self._bot.prefix +
                                           '%s** %s' % (name.replace('_', ' ', 1),
                                                        (self._bot.get_doc(command).strip()).split('\n', 1)[0])
                                           for (name, command) in clazz_commands[clazz]
                                           if name != 'help' and not command._err_command_hidden and
                                           (not self.bot_config.HIDE_RESTRICTED_COMMANDS or may_access_command(name))
                                           ]))
            usage += '\n\n'
        elif args in (clazz.__name__ for clazz in self._bot.get_command_classes()):
            # filter out the commands related to this class
            commands = [(name, command) for (name, command) in self._bot.commands.items() if
                        get_class_that_defined_method(command).__name__ == args]
            description = '### Available commands for %s\n\n' % args
            usage += '\n'.join(sorted([
                '- **' + self._bot.prefix + '%s** \- %s' % (name.replace('_', ' ', 1),
                                                            (self._bot.get_doc(command).strip()).split('\n', 1)[0])
                for (name, command) in commands
                if not command._err_command_hidden and
                (not self.bot_config.HIDE_RESTRICTED_COMMANDS or may_access_command(name))
            ]))
        else:
            description = ''
            if args in self._bot.commands:
                usage = (self._bot.commands[args].__doc__ or
                         'undocumented').strip()
            else:
                usage = self.MSG_HELP_UNDEFINED_COMMAND

        top = self._bot.top_of_help_message()
        bottom = self._bot.bottom_of_help_message()
        return ''.join(filter(None, [top, description, usage, bottom]))
