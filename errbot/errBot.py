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
import inspect
import logging
import os
from tarfile import TarFile
from urllib.request import urlopen

from . import botcmd, PY2
from .backends.base import Backend, ACLViolation
from .utils import (get_sender_username,
                    get_class_that_defined_method)
from .version import VERSION
from .streaming import Tee
from .plugin_manager import BotPluginManager, check_dependencies, PluginConfigurationException

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

    def callback_message(self, mess):
        if super(ErrBot, self).callback_message(mess):
            # Act only in the backend tells us that this message is OK to broadcast
            for bot in self.get_all_active_plugin_objects():
                # noinspection PyBroadException
                try:
                    log.debug('Trigger callback_message on %s' % bot.__class__.__name__)

                    # backward compatibility from the time we needed conn
                    if len(inspect.getargspec(bot.callback_message).args) == 3:
                        logging.warning('Deprecation: Plugin %s uses the old callback_message convention, '
                                        'now the signature should be simply def callback_message(self, mess)'
                                        % bot.__class__.__name__)
                        bot.callback_message(None, mess)
                    else:
                        bot.callback_message(mess)
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
        self.inject_commands_from(self)

    def disconnect_callback(self):
        self.remove_commands_from(self)
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
        return (get_class_that_defined_method(command) for command in self.commands.values())
