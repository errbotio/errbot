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

        cls_commands = {}
        for (name, command) in self._bot.all_commands.items():
            cls = get_class_that_defined_method(command)
            cls = str.__module__ + '.' + cls.__name__  # makes the fuul qualified name
            commands = cls_commands.get(cls, [])
            if not self.bot_config.HIDE_RESTRICTED_COMMANDS or self._bot.check_command_access(mess, name)[0]:
                commands.append((name, command))
                cls_commands[cls] = commands

        usage = ''
        for cls in sorted(cls_commands):
            usage += '\n'.join(sorted([
                '\t' + self._bot.prefix + '%s: %s' % (
                    name.replace('_', ' ', 1),
                    (command.__doc__ or '(undocumented)').strip().split('\n', 1)[0]
                )
                for (name, command) in cls_commands[cls]
                if args is not None and
                command.__doc__ is not None and
                args.lower() in command.__doc__.lower() and
                name != 'help' and not command._err_command_hidden
            ]))
        usage += '\n\n'

        return ''.join(filter(None, [description, usage])).strip()

    @botcmd
    def help(self, mess, args):
        """   Returns a help string listing available options.

        Automatically assigned to the "help" command."""

        def may_access_command(msg, cmd):
            msg, _, _ = self._bot._process_command_filters(msg, cmd, None, True)
            return msg is not None

        usage = ''
        if not args:
            description = '### Available help\n\n'
            command_classes = sorted(set(self._bot.get_command_classes()), key=lambda c: c.__name__)
            usage = '\n'.join(
                '- **' + self._bot.prefix + 'help %s** \- %s' %
                (cls.__name__, cls.__errdoc__.strip() or '(undocumented)') for cls in command_classes)
        elif args == 'full':
            description = '### Available commands\n\n'

            cls_commands = {}
            for (name, command) in self._bot.all_commands.items():
                cls = get_class_that_defined_method(command)
                commands = cls_commands.get(cls, [])
                if not self.bot_config.HIDE_RESTRICTED_COMMANDS or may_access_command(mess, name):
                    commands.append((name, command))
                    cls_commands[cls] = commands

            for cls in sorted(set(cls_commands), key=lambda c: c.__name__):
                usage += '\n\n**%s** \- %s\n' % (cls.__name__, cls.__errdoc__ or '')
                usage += '\n'.join(sorted(['**' +
                                           self._bot.prefix +
                                           '%s** %s' % (name.replace('_', ' ', 1),
                                                        (self._bot.get_doc(command).strip()).split('\n', 1)[0])
                                           for (name, command) in cls_commands[cls]
                                           if name != 'help' and not command._err_command_hidden and
                                           (not self.bot_config.HIDE_RESTRICTED_COMMANDS or
                                            may_access_command(mess, name))
                                           ]))
            usage += '\n\n'
        elif args in (cls.__name__ for cls in self._bot.get_command_classes()):
            # filter out the commands related to this class
            commands = [(name, command) for (name, command) in self._bot.all_commands.items() if
                        get_class_that_defined_method(command).__name__ == args]
            description = '### Available commands for %s\n\n' % args
            usage += '\n'.join(sorted([
                '- **' + self._bot.prefix + '%s** \- %s' % (name.replace('_', ' ', 1),
                                                            (self._bot.get_doc(command).strip()).split('\n', 1)[0])
                for (name, command) in commands
                if not command._err_command_hidden and
                (not self.bot_config.HIDE_RESTRICTED_COMMANDS or may_access_command(mess, name))
            ]))
        else:
            description = ''
            all_commands = dict(self._bot.all_commands)
            all_commands.update(
                {k.replace('_', ' '): v for k, v in all_commands.items()})
            if args in all_commands:
                usage = (all_commands[args].__doc__ or 'undocumented').strip()
            else:
                usage = self.MSG_HELP_UNDEFINED_COMMAND

        return ''.join(filter(None, [description, usage]))
