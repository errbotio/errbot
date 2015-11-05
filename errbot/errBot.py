# -*- coding: utf-8 -*-

#    This program is free software; you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation; either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program; if not, write to the Free Software
#    Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
from datetime import datetime
import difflib
import inspect
import logging
import traceback

from .bundled.threadpool import ThreadPool, WorkRequest

from .backends.base import Backend
from .utils import (split_string_after,
                    get_class_that_defined_method, compat_str)
from .streaming import Tee
from .plugin_manager import BotPluginManager
from .templating import tenv

log = logging.getLogger(__name__)


def bot_config_defaults(config):
    if not hasattr(config, 'ACCESS_CONTROLS_DEFAULT'):
        config.ACCESS_CONTROLS_DEFAULT = {}
    if not hasattr(config, 'ACCESS_CONTROLS'):
        config.ACCESS_CONTROLS = {}
    if not hasattr(config, 'HIDE_RESTRICTED_COMMANDS'):
        config.HIDE_RESTRICTED_COMMANDS = False
    if not hasattr(config, 'HIDE_RESTRICTED_ACCESS'):
        config.HIDE_RESTRICTED_ACCESS = False
    if not hasattr(config, 'BOT_PREFIX_OPTIONAL_ON_CHAT'):
        config.BOT_PREFIX_OPTIONAL_ON_CHAT = False
    if not hasattr(config, 'BOT_ALT_PREFIXES'):
        config.BOT_ALT_PREFIXES = ()
    if not hasattr(config, 'BOT_ALT_PREFIX_SEPARATORS'):
        config.BOT_ALT_PREFIX_SEPARATORS = ()
    if not hasattr(config, 'BOT_ALT_PREFIX_CASEINSENSITIVE'):
        config.BOT_ALT_PREFIX_CASEINSENSITIVE = False
    if not hasattr(config, 'DIVERT_TO_PRIVATE'):
        config.DIVERT_TO_PRIVATE = ()
    if not hasattr(config, 'MESSAGE_SIZE_LIMIT'):
        config.MESSAGE_SIZE_LIMIT = 10000  # Corresponds with what HipChat accepts
    if not hasattr(config, 'GROUPCHAT_NICK_PREFIXED'):
        config.GROUPCHAT_NICK_PREFIXED = False
    if not hasattr(config, 'AUTOINSTALL_DEPS'):
        config.AUTOINSTALL_DEPS = False
    if not hasattr(config, 'SUPPRESS_CMD_NOT_FOUND'):
        config.SUPPRESS_CMD_NOT_FOUND = False


class ErrBot(Backend, BotPluginManager):
    """ ErrBot is the layer of Err that takes care of the plugin management and dispatching
    """
    __errdoc__ = """ Commands related to the bot administration """
    MSG_ERROR_OCCURRED = 'Computer says nooo. See logs for details.'
    MSG_UNKNOWN_COMMAND = 'Unknown command: "%(command)s". '
    startup_time = datetime.now()

    def __init__(self, bot_config):
        log.debug("ErrBot init.")
        super(ErrBot, self).__init__(bot_config)
        self._init_plugin_manager(bot_config)
        self.bot_config = bot_config
        self.prefix = bot_config.BOT_PREFIX
        if bot_config.BOT_ASYNC:
            self.thread_pool = ThreadPool(3)
            log.debug('created the thread pool' + str(self.thread_pool))
        self.commands = {}  # the dynamically populated list of commands available on the bot
        self.re_commands = {}  # the dynamically populated list of regex-based commands available on the bot
        self.command_filters = []  # the dynamically populated list of filters
        self.MSG_UNKNOWN_COMMAND = 'Unknown command: "%(command)s". ' \
                                   'Type "' + bot_config.BOT_PREFIX + 'help" for available commands.'
        if bot_config.BOT_ALT_PREFIX_CASEINSENSITIVE:
            self.bot_alt_prefixes = tuple(prefix.lower() for prefix in bot_config.BOT_ALT_PREFIXES)
        else:
            self.bot_alt_prefixes = bot_config.BOT_ALT_PREFIXES

    @property
    def all_commands(self):
        """Return both commands and re_commands together."""
        newd = dict(**self.commands)
        newd.update(self.re_commands)
        return newd

    def _dispatch_to_plugins(self, method, *args, **kwargs):
        """
        Dispatch the given method to all active plugins.

        Will catch and log any exceptions that occur.

        :param method: The name of the function to dispatch.
        :param *args: Passed to the callback function.
        :param **kwargs: Passed to the callback function.
        """
        for plugin in self.get_all_active_plugin_objects():
            plugin_name = plugin.__class__.__name__
            log.debug("Triggering {} on {}".format(method, plugin_name))
            # noinspection PyBroadException
            try:
                getattr(plugin, method)(*args, **kwargs)
            except Exception:
                log.exception("{} on {} crashed".format(method, plugin_name))

    def send_message(self, mess):
        for bot in self.get_all_active_plugin_objects():
            # noinspection PyBroadException
            try:
                bot.callback_botmessage(mess)
            except Exception:
                log.exception("Crash in a callback_botmessage handler")

    def send_simple_reply(self, mess, text, private=False):
        """Send a simple response to a message"""
        self.send_message(self.build_reply(mess, text, private))

    def process_message(self, mess):
        """Check if the given message is a command for the bot and act on it.
        It return True for triggering the callback_messages on the .callback_messages on the plugins.
        """
        # Prepare to handle either private chats or group chats
        type_ = mess.type
        frm = mess.frm
        text = mess.body
        if not hasattr(mess.frm, 'person'):
            raise Exception('mess.frm not an Identifier as it misses the "person" property. Class of frm : %s'
                            % mess.frm.__class__)

        username = mess.frm.person
        user_cmd_history = self.cmd_history[username]

        if mess.delayed:
            log.debug("Message from history, ignore it")
            return False

        if type_ not in ("groupchat", "chat"):
            log.debug("unhandled message type %s" % mess)
            return False

        if (frm.person == self.bot_identifier.person or
            type_ == "groupchat" and mess.frm.nick == self.bot_config.CHATROOM_FN):  # noqa
                log.debug("Ignoring message from self")
                return False

        log.debug("*** frm = %s" % frm)
        log.debug("*** username = %s" % username)
        log.debug("*** type = %s" % type_)
        log.debug("*** text = %s" % text)

        suppress_cmd_not_found = self.bot_config.SUPPRESS_CMD_NOT_FOUND

        prefixed = False  # Keeps track whether text was prefixed with a bot prefix
        only_check_re_command = False  # Becomes true if text is determed to not be a regular command
        tomatch = text.lower() if self.bot_config.BOT_ALT_PREFIX_CASEINSENSITIVE else text
        if len(self.bot_config.BOT_ALT_PREFIXES) > 0 and tomatch.startswith(self.bot_alt_prefixes):
            # Yay! We were called by one of our alternate prefixes. Now we just have to find out
            # which one... (And find the longest matching, in case you have 'err' and 'errbot' and
            # someone uses 'errbot', which also matches 'err' but would leave 'bot' to be taken as
            # part of the called command in that case)
            prefixed = True
            longest = 0
            for prefix in self.bot_alt_prefixes:
                l = len(prefix)
                if tomatch.startswith(prefix) and l > longest:
                    longest = l
            log.debug("Called with alternate prefix '{}'".format(text[:longest]))
            text = text[longest:]

            # Now also remove the separator from the text
            for sep in self.bot_config.BOT_ALT_PREFIX_SEPARATORS:
                # While unlikely, one may have separators consisting of
                # more than one character
                l = len(sep)
                if text[:l] == sep:
                    text = text[l:]
        elif type_ == "chat" and self.bot_config.BOT_PREFIX_OPTIONAL_ON_CHAT:
            log.debug("Assuming '%s' to be a command because BOT_PREFIX_OPTIONAL_ON_CHAT is True" % text)
            # In order to keep noise down we surpress messages about the command
            # not being found, because it's possible a plugin will trigger on what
            # was said with trigger_message.
            suppress_cmd_not_found = True
        elif not text.startswith(self.bot_config.BOT_PREFIX):
            only_check_re_command = True
        if text.startswith(self.bot_config.BOT_PREFIX):
            text = text[len(self.bot_config.BOT_PREFIX):]
            prefixed = True

        text = text.strip()
        text_split = text.split(' ')
        cmd = None
        command = None
        args = ''
        if not only_check_re_command:
            if len(text_split) > 1:
                command = (text_split[0] + '_' + text_split[1]).lower()
                if command in self.commands:
                    cmd = command
                    args = ' '.join(text_split[2:])

            if not cmd:
                command = text_split[0].lower()
                args = ' '.join(text_split[1:])
                if command in self.commands:
                    cmd = command
                    if len(text_split) > 1:
                        args = ' '.join(text_split[1:])

            if command == self.bot_config.BOT_PREFIX:  # we did "!!" so recall the last command
                if len(user_cmd_history):
                    cmd, args = user_cmd_history[-1]
                else:
                    return False  # no command in history
            elif command.isdigit():  # we did "!#" so we recall the specified command
                index = int(command)
                if len(user_cmd_history) >= index:
                    cmd, args = user_cmd_history[-index]
                else:
                    return False  # no command in history

        # Try to match one of the regex commands if the regular commands produced no match
        matched_on_re_command = False
        if not cmd:
            if prefixed or (type_ == "chat" and self.bot_config.BOT_PREFIX_OPTIONAL_ON_CHAT):
                commands = self.re_commands
            else:
                commands = {k: self.re_commands[k] for k in self.re_commands
                            if not self.re_commands[k]._err_command_prefix_required}

            for name, func in commands.items():
                if func._err_command_matchall:
                    match = list(func._err_command_re_pattern.finditer(text))
                else:
                    match = func._err_command_re_pattern.search(text)
                if match:
                    log.debug("Matching '{}' against '{}' produced a match"
                              .format(text, func._err_command_re_pattern.pattern))
                    matched_on_re_command = True
                    self._process_command(mess, name, text, match)
                else:
                    log.debug("Matching '{}' against '{}' produced no match"
                              .format(text, func._err_command_re_pattern.pattern))
        if matched_on_re_command:
            return True

        if cmd:
            self._process_command(mess, cmd, args, match=None)
        elif not only_check_re_command:
            log.debug("Command not found")
            if suppress_cmd_not_found:
                log.debug("Surpressing command not found feedback")
            else:
                reply = self.unknown_command(mess, command, args)
                if reply is None:
                    reply = self.MSG_UNKNOWN_COMMAND % {'command': command}
                if reply:
                    self.send_simple_reply(mess, reply)
        return True

    def _process_command_filters(self, msg, cmd, args, dry_run=False):
        try:
            for cmd_filter in self.command_filters:
                msg, cmd, args = cmd_filter(msg, cmd, args, dry_run)
                if msg is None:
                    return None, None, None
            return msg, cmd, args
        except Exception:
            log.exception("Exception in a filter command, blocking the command in doubt")
            return None, None, None

    def _process_command(self, mess, cmd, args, match):
        """Process and execute a bot command"""

        # first it must go through the command filters
        mess, cmd, args = self._process_command_filters(mess, cmd, args, False)
        if mess is None:
            log.info("Command %s blocked or deferred." % cmd)
            return

        frm = mess.frm
        username = frm.person
        user_cmd_history = self.cmd_history[username]

        log.info("Processing command '{}' with parameters '{}' from {}".format(cmd, args, frm))

        if (cmd, args) in user_cmd_history:
            user_cmd_history.remove((cmd, args))  # Avoids duplicate history items

        f = self.re_commands[cmd] if match else self.commands[cmd]

        if f._err_command_admin_only and self.bot_config.BOT_ASYNC:
            # If it is an admin command, wait until the queue is completely depleted so
            # we don't have strange concurrency issues on load/unload/updates etc...
            self.thread_pool.wait()

        if f._err_command_historize:
            user_cmd_history.append((cmd, args))  # add it to the history only if it is authorized to be so

        # Don't check for None here as None can be a valid argument to str.split.
        # '' was chosen as default argument because this isn't a valid argument to str.split()
        if not match and f._err_command_split_args_with != '':
            try:
                if hasattr(f._err_command_split_args_with, "parse_args"):
                    args = f._err_command_split_args_with.parse_args(args)
                elif callable(f._err_command_split_args_with):
                    args = f._err_command_split_args_with(args)
                else:
                    args = args.split(f._err_command_split_args_with)
            except Exception as e:
                self.send_simple_reply(
                    mess,
                    "Sorry, I couldn't parse your arguments. {}".format(e)
                )
                return

        if self.bot_config.BOT_ASYNC:
            wr = WorkRequest(
                self._execute_and_send,
                [],
                {'cmd': cmd, 'args': args, 'match': match, 'mess': mess,
                 'template_name': f._err_command_template}
            )
            self.thread_pool.putRequest(wr)
            if f._err_command_admin_only:
                # Again, if it is an admin command, wait until the queue is completely
                # depleted so we don't have strange concurrency issues.
                self.thread_pool.wait()
        else:
            self._execute_and_send(cmd=cmd, args=args, match=match, mess=mess,
                                   template_name=f._err_command_template)

    def _execute_and_send(self, cmd, args, match, mess, template_name=None):
        """Execute a bot command and send output back to the caller

        cmd: The command that was given to the bot (after being expanded)
        args: Arguments given along with cmd
        match: A re.MatchObject if command is coming from a regex-based command, else None
        mess: The message object
        template_name: The name of the jinja template which should be used to render
            the markdown output, if any

        """
        def process_reply(reply_):
            # integrated templating
            if template_name:
                reply_ = tenv().get_template(template_name + '.md').render(**reply_)

            # Reply should be all text at this point (See https://github.com/gbin/err/issues/96)
            return str(reply_)

        def send_reply(reply_):
            for part in split_string_after(reply_, self.bot_config.MESSAGE_SIZE_LIMIT):
                self.send_simple_reply(mess, part, cmd in self.bot_config.DIVERT_TO_PRIVATE)

        commands = self.re_commands if match else self.commands
        try:
            if inspect.isgeneratorfunction(commands[cmd]):
                replies = commands[cmd](mess, match) if match else commands[cmd](mess, args)
                for reply in replies:
                    if reply:
                        send_reply(process_reply(reply))
            else:
                reply = commands[cmd](mess, match) if match else commands[cmd](mess, args)
                if reply:
                    send_reply(process_reply(reply))
        except Exception as e:
            tb = traceback.format_exc()
            log.exception('An error happened while processing '
                          'a message ("%s"): %s"' %
                          (mess.body, tb))
            send_reply(self.MSG_ERROR_OCCURRED + ':\n %s' % e)

    def unknown_command(self, _, cmd, args):
        """ Override the default unknown command behavior
        """
        full_cmd = cmd + ' ' + args.split(' ')[0] if args else None
        if full_cmd:
            part1 = 'Command "%s" / "%s" not found.' % (cmd, full_cmd)
        else:
            part1 = 'Command "%s" not found.' % cmd
        ununderscore_keys = [m.replace('_', ' ') for m in self.all_commands.keys()]
        matches = difflib.get_close_matches(cmd, ununderscore_keys)
        if full_cmd:
            matches.extend(difflib.get_close_matches(full_cmd, ununderscore_keys))
        matches = set(matches)
        if matches:
            return (part1 + '\n\nDid you mean "' + self.bot_config.BOT_PREFIX +
                    ('" or "' + self.bot_config.BOT_PREFIX).join(matches) + '" ?')
        else:
            return part1

    def inject_commands_from(self, instance_to_inject):
        classname = instance_to_inject.__class__.__name__
        for name, value in inspect.getmembers(instance_to_inject, inspect.ismethod):
            if getattr(value, '_err_command', False):
                commands = self.re_commands if getattr(value, '_err_re_command') else self.commands
                name = getattr(value, '_err_command_name')

                if name in commands:
                    f = commands[name]
                    new_name = (classname + '-' + name).lower()
                    self.warn_admins('%s.%s clashes with %s.%s so it has been renamed %s' % (
                        classname, name, type(f.__self__).__name__, f.__name__, new_name))
                    name = new_name
                commands[name] = value

                if getattr(value, '_err_re_command'):
                    log.debug('Adding regex command : %s -> %s' % (name, value.__name__))
                    self.re_commands = commands
                else:
                    log.debug('Adding command : %s -> %s' % (name, value.__name__))
                    self.commands = commands

    def inject_command_filters_from(self, instance_to_inject):
        classname = instance_to_inject.__class__.__name__
        for name, method in inspect.getmembers(instance_to_inject, inspect.ismethod):
            if getattr(method, '_err_command_filter', False):
                log.debug('Adding command filter: %s' % name)
                self.command_filters.append(method)

    def remove_commands_from(self, instance_to_inject):
        for name, value in inspect.getmembers(instance_to_inject, inspect.ismethod):
            if getattr(value, '_err_command', False):
                name = getattr(value, '_err_command_name')
                if getattr(value, '_err_re_command') and name in self.re_commands:
                    del (self.re_commands[name])
                elif not getattr(value, '_err_re_command') and name in self.commands:
                    del (self.commands[name])

    def remove_command_filters_from(self, instance_to_inject):
        for name, method in inspect.getmembers(instance_to_inject, inspect.ismethod):
            if getattr(method, '_err_command_filter', False):
                log.debug('Removing command filter: %s' % name)
                self.command_filters.remove(method)

    def warn_admins(self, warning):
        for admin in self.bot_config.BOT_ADMINS:
            self.send(admin, warning)

    def top_of_help_message(self):
        """Returns a string that forms the top of the help message

        Override this method in derived class if you
        want to add additional help text at the
        beginning of the help message.
        """
        return ""

    def bottom_of_help_message(self):
        """Returns a string that forms the bottom of the help message

        Override this method in derived class if you
        want to add additional help text at the end
        of the help message.
        """
        return ""

    def send(self, user, text, in_reply_to=None, message_type='chat', groupchat_nick_reply=False):
        """ Sends a simple message to the specified user.
            :param user:
                an identifier from build_identifier or from an incoming message
            :param in_reply_to:
                the original message the bot is answering from
            :param text:
                the markdown text you want to send
            :param message_type:
                chat or groupchat
            :param groupchat_nick_reply:
                authorized the prefixing with the nick form the user
        """
        if not hasattr(user, 'person'):
            log.debug("user is not an identifier, build one")
            user = self.build_identifier(user)

        mess = self.build_message(text)
        mess.to = user

        if in_reply_to:
            mess.type = in_reply_to.type
            mess.frm = in_reply_to.to
        else:
            mess.type = message_type
            mess.frm = self.bot_identifier

        nick_reply = self.bot_config.GROUPCHAT_NICK_PREFIXED
        if message_type == 'groupchat' and in_reply_to and nick_reply and groupchat_nick_reply:
            self.prefix_groupchat_reply(mess, in_reply_to.frm)

        self.send_message(mess)

    def callback_message(self, mess):
        """Processes for commands and dispatches the message to all the plugins."""
        if self.process_message(mess):
            # Act only in the backend tells us that this message is OK to broadcast
            for plugin in self.get_all_active_plugin_objects():
                # noinspection PyBroadException
                try:
                    log.debug('Trigger callback_message on %s' % plugin.__class__.__name__)
                    plugin.callback_message(mess)
                except Exception:
                    log.exception("Crash in a callback_message handler")

    def callback_presence(self, pres):
        self._dispatch_to_plugins('callback_presence', pres)

    def callback_room_joined(self, room):
        """
            Triggered when the bot has joined a MUC.

            :param room:
                An instance of :class:`~errbot.backends.base.MUCRoom`
                representing the room that was joined.
        """
        self._dispatch_to_plugins('callback_room_joined', room)

    def callback_room_left(self, room):
        """
            Triggered when the bot has left a MUC.

            :param room:
                An instance of :class:`~errbot.backends.base.MUCRoom`
                representing the room that was left.
        """
        self._dispatch_to_plugins('callback_room_left', room)

    def callback_room_topic(self, room):
        """
            Triggered when the topic in a MUC changes.

            :param room:
                An instance of :class:`~errbot.backends.base.MUCRoom`
                representing the room for which the topic changed.
        """
        self._dispatch_to_plugins('callback_room_topic', room)

    def callback_stream(self, stream):
        log.info("Initiated an incoming transfer %s" % stream)
        Tee(stream, self.get_all_active_plugin_objects()).start()

    def signal_connect_to_all_plugins(self):
        for bot in self.get_all_active_plugin_objects():
            if hasattr(bot, 'callback_connect'):
                # noinspection PyBroadException
                try:
                    log.debug('Trigger callback_connect on %s' % bot.__class__.__name__)
                    bot.callback_connect()
                except Exception:
                    log.exception("callback_connect failed for %s" % bot)

    def connect_callback(self):
        log.info('Activate internal commands')
        loading_errors = self.activate_non_started_plugins()
        log.info(loading_errors)
        log.info('Notifying connection to all the plugins...')
        self.signal_connect_to_all_plugins()
        log.info('Plugin activation done.')

    def disconnect_callback(self):
        log.info('Disconnect callback, deactivating all the plugins.')
        self.deactivate_all_plugins()

    def get_doc(self, command):
        """Get command documentation
        """
        if not command.__doc__:
            return '(undocumented)'
        if self.prefix == '!':
            return command.__doc__
        return command.__doc__.replace('!', self.prefix)

    def get_command_classes(self):
        return (get_class_that_defined_method(command)
                for command in self.all_commands.values())
