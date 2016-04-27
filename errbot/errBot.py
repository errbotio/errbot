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

from errbot import CommandError
from errbot.flow import FlowExecutor, FlowRoot
from .backends.base import Backend, Room, Identifier, Person, Message
from threadpool import ThreadPool, WorkRequest
from threading import RLock
from .streaming import Tee
from .templating import tenv
from .utils import (split_string_after,
                    get_class_that_defined_method, compat_str)
from .storage import StoreMixin

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


# noinspection PyAbstractClass
class ErrBot(Backend, StoreMixin):
    """ ErrBot is the layer of Err that takes care of the plugin management and dispatching
    """
    __errdoc__ = """ Commands related to the bot administration """
    MSG_ERROR_OCCURRED = 'Computer says nooo. See logs for details'
    MSG_UNKNOWN_COMMAND = 'Unknown command: "%(command)s". '
    startup_time = datetime.now()

    def __init__(self, bot_config):
        log.debug("ErrBot init.")
        super().__init__(bot_config)
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
        self.repo_manager = None
        self.plugin_manager = None
        self.storage_plugin = None
        self._plugin_errors_during_startup = None
        self.flow_executor = FlowExecutor(self)
        self._gbl = RLock()  # this protects internal structures of this class

    def attach_repo_manager(self, repo_manager):
        self.repo_manager = repo_manager

    def attach_plugin_manager(self, plugin_manager):
        self.plugin_manager = plugin_manager
        plugin_manager.attach_bot(self)

    def attach_storage_plugin(self, storage_plugin):
        # the storage_plugin is needed by the plugins
        self.storage_plugin = storage_plugin

    def initialize_backend_storage(self):
        """
        Initialize storage for the backend to use.
        """
        log.debug("Initializing backend storage")
        assert self.plugin_manager is not None
        assert self.storage_plugin is not None
        self.open_storage(self.storage_plugin, '%s_backend' % self.mode)

    @property
    def all_commands(self):
        """Return both commands and re_commands together."""
        with self._gbl:
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
        for plugin in self.plugin_manager.get_all_active_plugin_objects():
            plugin_name = plugin.__class__.__name__
            log.debug("Triggering {} on {}".format(method, plugin_name))
            # noinspection PyBroadException
            try:
                getattr(plugin, method)(*args, **kwargs)
            except Exception:
                log.exception("{} on {} crashed".format(method, plugin_name))

    def send(self, identifier, text, in_reply_to=None, groupchat_nick_reply=False):
        """ Sends a simple message to the specified user.

            :param identifier:
                an identifier from build_identifier or from an incoming message
            :param in_reply_to:
                the original message the bot is answering from
            :param text:
                the markdown text you want to send
            :param groupchat_nick_reply:
                authorized the prefixing with the nick form the user
        """
        # protect a little bit the backends here
        if not isinstance(identifier, Identifier):
            raise ValueError("identifier should be an Identifier")

        mess = self.build_message(text)
        mess.to = identifier
        mess.frm = in_reply_to.to if in_reply_to else self.bot_identifier

        nick_reply = self.bot_config.GROUPCHAT_NICK_PREFIXED
        if isinstance(identifier, Room) and in_reply_to and (nick_reply or groupchat_nick_reply):
            self.prefix_groupchat_reply(mess, in_reply_to.frm)

        self.split_and_send_message(mess)

    def send_templated(self, identifier, template_name, template_parameters, in_reply_to=None,
                       groupchat_nick_reply=False):
        """ Sends a simple message to the specified user using a template.

            :param template_parameters: the parameters for the template.
            :param template_name: the template name you want to use.
            :param identifier:
                an identifier from build_identifier or from an incoming message, a room etc.
            :param in_reply_to:
                the original message the bot is answering from
            :param groupchat_nick_reply:
                authorized the prefixing with the nick form the user
        """
        text = self.process_template(template_name, template_parameters)
        return self.send(identifier, text, in_reply_to, groupchat_nick_reply)

    def split_and_send_message(self, mess):
        for part in split_string_after(mess.body, self.bot_config.MESSAGE_SIZE_LIMIT):
            partial_message = mess.clone()
            partial_message.body = part
            self.send_message(partial_message)

    def send_message(self, mess):
        """
        This needs to be overridden by the backends with a super() call.

        :param mess: the message to send.
        :return: None
        """
        for bot in self.plugin_manager.get_all_active_plugin_objects():
            # noinspection PyBroadException
            try:
                bot.callback_botmessage(mess)
            except Exception:
                log.exception("Crash in a callback_botmessage handler")

    def send_card(self, card):
        """
        Sends a card, this can be overriden by the backends *without* a super() call.

        :param card: the card to send.
        :return: None
        """
        self.send_templated(card.to, 'card', {'card': card})

    def send_simple_reply(self, mess, text, private=False):
        """Send a simple response to a given incoming message

        :param private: if True will force a response in private.
        :param text: the markdown text of the message.
        :param mess: the message you are replying to.
        """
        reply = self.build_reply(mess, text, private)
        if isinstance(reply.to, Room) and self.bot_config.GROUPCHAT_NICK_PREFIXED:
            self.prefix_groupchat_reply(reply, mess.frm)
        self.split_and_send_message(reply)

    def process_message(self, mess):
        """Check if the given message is a command for the bot and act on it.
        It return True for triggering the callback_messages on the .callback_messages on the plugins.

        :param mess: the incoming message.
        """
        # Prepare to handle either private chats or group chats

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

        if (mess.is_direct and frm == self.bot_identifier) or \
                (mess.is_group and frm.nick == self.bot_config.CHATROOM_FN):
            log.debug("Ignoring message from self")
            return False

        log.debug("*** frm = %s" % frm)
        log.debug("*** username = %s" % username)
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
        elif mess.is_direct and self.bot_config.BOT_PREFIX_OPTIONAL_ON_CHAT:
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
                with self._gbl:
                    if command in self.commands:
                        cmd = command
                        args = ' '.join(text_split[2:])

            if not cmd:
                command = text_split[0].lower()
                args = ' '.join(text_split[1:])
                with self._gbl:
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
            with self._gbl:
                if prefixed or (mess.is_direct and self.bot_config.BOT_PREFIX_OPTIONAL_ON_CHAT):
                    commands = dict(self.re_commands)
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

        with self._gbl:
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

    @staticmethod
    def process_template(template_name, template_parameters):
        # integrated templating
        if template_name:
            return tenv().get_template(template_name + '.md').render(**template_parameters)

        # Reply should be all text at this point (See https://github.com/errbotio/errbot/issues/96)
        return str(template_parameters)

    def _execute_and_send(self, cmd, args, match, mess, template_name=None):
        """Execute a bot command and send output back to the caller

        cmd: The command that was given to the bot (after being expanded)
        args: Arguments given along with cmd
        match: A re.MatchObject if command is coming from a regex-based command, else None
        mess: The message object
        template_name: The name of the jinja template which should be used to render
            the markdown output, if any

        """
        private = cmd in self.bot_config.DIVERT_TO_PRIVATE
        commands = self.re_commands if match else self.commands
        try:
            with self._gbl:
                method = commands[cmd]
            # first check if we need to reattach a flow context
            flow, _ = self.flow_executor.check_inflight_flow_triggered(cmd, mess.frm)
            if flow:
                log.debug("Reattach context from flow %s to the message", flow._root.name)
                mess.ctx = flow.ctx
            elif method._err_command_flow_only:
                # check if it is a flow_only command but we are not in a flow.
                log.debug("%s is tagged flow_only and we are not in a flow. Ignores the command.", cmd)
                return

            if inspect.isgeneratorfunction(method):
                replies = method(mess, match) if match else method(mess, args)
                for reply in replies:
                    if reply:
                        self.send_simple_reply(mess, self.process_template(template_name, reply), private)
            else:
                reply = method(mess, match) if match else method(mess, args)
                if reply:
                    self.send_simple_reply(mess, self.process_template(template_name, reply), private)

            # The command is a success, check if this has not made a flow progressed
            self.flow_executor.trigger(cmd, mess.frm, mess.ctx)

        except CommandError as command_error:
            reason = command_error.reason
            if command_error.template:
                reason = self.process_template(command_error.template, reason)
            self.send_simple_reply(mess, reason, private)

        except Exception as e:
            tb = traceback.format_exc()
            log.exception('An error happened while processing '
                          'a message ("%s"): %s"' %
                          (mess.body, tb))
            self.send_simple_reply(mess, self.MSG_ERROR_OCCURRED + ':\n %s' % e, private)

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
        with self._gbl:
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
                        value.__func__._err_command_name = new_name  # To keep track of the renaming.
                    commands[name] = value

                    if getattr(value, '_err_re_command'):
                        log.debug('Adding regex command : %s -> %s' % (name, value.__name__))
                        self.re_commands = commands
                    else:
                        log.debug('Adding command : %s -> %s' % (name, value.__name__))
                        self.commands = commands

    def inject_flows_from(self, instance_to_inject):
        classname = instance_to_inject.__class__.__name__
        for name, method in inspect.getmembers(instance_to_inject, inspect.ismethod):
            if getattr(method, '_err_flow', False):
                log.debug('Found new flow %s: %s', classname, name)
                flow = FlowRoot(name, method.__doc__)
                try:
                    method(flow)
                except Exception:
                    log.exception("Exception initializing a flow")

                self.flow_executor.add_flow(flow)

    def inject_command_filters_from(self, instance_to_inject):
        with self._gbl:
            for name, method in inspect.getmembers(instance_to_inject, inspect.ismethod):
                if getattr(method, '_err_command_filter', False):
                    log.debug('Adding command filter: %s' % name)
                    self.command_filters.append(method)

    def remove_flows_from(self, instance_to_inject):
        for name, value in inspect.getmembers(instance_to_inject, inspect.ismethod):
            if getattr(value, '_err_flow', False):
                log.debug('Remove flow %s', name)
                # TODO(gbin)

    def remove_commands_from(self, instance_to_inject):
        with self._gbl:
            for name, value in inspect.getmembers(instance_to_inject, inspect.ismethod):
                if getattr(value, '_err_command', False):
                    name = getattr(value, '_err_command_name')
                    if getattr(value, '_err_re_command') and name in self.re_commands:
                        del self.re_commands[name]
                    elif not getattr(value, '_err_re_command') and name in self.commands:
                        del self.commands[name]

    def remove_command_filters_from(self, instance_to_inject):
        with self._gbl:
            for name, method in inspect.getmembers(instance_to_inject, inspect.ismethod):
                if getattr(method, '_err_command_filter', False):
                    log.debug('Removing command filter: %s' % name)
                    self.command_filters.remove(method)

    def warn_admins(self, warning):
        for admin in self.bot_config.BOT_ADMINS:
            self.send(self.build_identifier(admin), warning)

    def callback_message(self, mess):
        """Processes for commands and dispatches the message to all the plugins."""
        if self.process_message(mess):
            # Act only in the backend tells us that this message is OK to broadcast
            self._dispatch_to_plugins('callback_message', mess)

    def callback_mention(self, mess, people):
        log.debug("%s has/have been mentioned", ', '.join(str(p) for p in people))
        self._dispatch_to_plugins('callback_mention', mess, people)

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
        Tee(stream, self.plugin_manager.get_all_active_plugin_objects()).start()

    def signal_connect_to_all_plugins(self):
        for bot in self.plugin_manager.get_all_active_plugin_objects():
            if hasattr(bot, 'callback_connect'):
                # noinspection PyBroadException
                try:
                    log.debug('Trigger callback_connect on %s' % bot.__class__.__name__)
                    bot.callback_connect()
                except Exception:
                    log.exception("callback_connect failed for %s" % bot)

    def connect_callback(self):
        log.info('Activate internal commands')
        if self._plugin_errors_during_startup:
            errors = "Some plugins failed to start during bot startup:\n\n{errors}".format(
                errors=self._plugin_errors_during_startup
            )
        else:
            errors = ""
        errors += self.plugin_manager.activate_non_started_plugins()
        if errors:
            self.warn_admins(errors)
        log.info(errors)
        log.info('Notifying connection to all the plugins...')
        self.signal_connect_to_all_plugins()
        log.info('Plugin activation done.')

    def disconnect_callback(self):
        log.info('Disconnect callback, deactivating all the plugins.')
        self.plugin_manager.deactivate_all_plugins()

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

    def shutdown(self):
        self.close_storage()
        self.plugin_manager.shutdown()
        self.repo_manager.shutdown()

    def prefix_groupchat_reply(self, message: Message, identifier: Identifier):
        if message.body.startswith('#'):
            # Markdown heading, insert an extra newline to ensure the
            # markdown rendering doesn't break.
            message.body = "\n" + message.body
