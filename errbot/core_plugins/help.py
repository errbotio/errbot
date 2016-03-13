import textwrap

from errbot import BotPlugin, botcmd
from errbot.version import VERSION
from errbot.utils import get_class_that_defined_method


class Help(BotPlugin):
    MSG_HELP_TAIL = 'Type help <command name> to get more info ' \
                    'about that specific command.'
    MSG_HELP_UNDEFINED_COMMAND = 'That command is not defined.'

    # noinspection PyUnusedLocal
    @botcmd(template='about')
    def about(self, mess, args):
        """Return information about this Errbot instance and version"""
        return {'version': VERSION}

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
        """Returns a help string listing available options.
        Automatically assigned to the "help" command."""

        def may_access_command(msg, cmd):
            msg, _, _ = self._bot._process_command_filters(
                msg=msg,
                cmd=cmd,
                args=None,
                dry_run=True
            )
            return msg is not None

        def get_name(named):
            return named.__name__.lower()

        # Normalize args to lowercase for ease of use
        args = args.lower() if args else ''
        usage = ''
        description = '### All commands\n'

        # show all
        if not args:
            cls_commands = {}
            for (name, command) in self._bot.all_commands.items():
                cls = get_class_that_defined_method(command)
                commands = cls_commands.get(cls, [])
                if not self.bot_config.HIDE_RESTRICTED_COMMANDS or may_access_command(mess, name):
                    commands.append((name, command))
                    cls_commands[cls] = commands

            for cls in sorted(set(cls_commands), key=lambda c: c.__name__):
                # shows class and description
                usage += '\n**{name}**\n\n*{doc}*\n\n'.format(
                                           name=cls.__name__,
                                           doc=cls.__errdoc__.strip() or '',
                                       )

                for (name, command) in cls_commands[cls]:
                    if command._err_command_hidden:
                        continue
                    # show individual commands
                    usage += self._cmd_help_line(name, command)
            usage += '\n\n'  # end cls section
        elif args in (get_name(cls) for cls in self._bot.get_command_classes()):
            # filter out the commands related to this class
            [cls] = {
                c for c in self._bot.get_command_classes()
                if get_name(c) == args
            }
            commands = [
                (name, command) for (name, command)
                in self._bot.all_commands.items() if
                get_name(get_class_that_defined_method(command)) == args]

            description = '\n**{name}**\n\n*{doc}*\n\n'.format(
                                       name=cls.__name__,
                                       doc=cls.__errdoc__.strip() or '',
                                   )
            pairs = sorted([
                (name, command)
                for (name, command) in commands
                if not command._err_command_hidden and
                (not self.bot_config.HIDE_RESTRICTED_COMMANDS or may_access_command(mess, name))
            ])

            for (name, command) in pairs:
                usage += self._cmd_help_line(name, command)
        else:
            description = ''
            all_commands = dict(self._bot.all_commands)
            all_commands.update(
                {k.replace('_', ' '): v for k, v in all_commands.items()})
            if args in all_commands:
                usage = self._cmd_help_line(args, all_commands[args], True)
            else:
                usage = self.MSG_HELP_UNDEFINED_COMMAND

        return ''.join(filter(None, [description, usage]))

    def _cmd_help_line(self, name, command, show_doc=False):
        """
        Returns:
            str. a single line indicating the help representation of a command.
        """
        cmd_name = name.replace('_', ' ')
        cmd_doc = textwrap.dedent(self._bot.get_doc(command)).strip()
        prefix = self._bot.prefix

        name = cmd_name
        patt = getattr(command, '_err_command_re_pattern', None)

        if patt:
            name = patt.pattern

        if not show_doc:
            cmd_doc = cmd_doc.split('\n')[0]

            if len(cmd_doc) > 80:
                cmd_doc = '{doc}...'.format(doc=cmd_doc[:77])

        help_str = '- **{prefix}{name}** - {doc}\n'.format(prefix=prefix, name=name, doc=cmd_doc)

        return help_str
