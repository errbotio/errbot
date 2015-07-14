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
import subprocess
from tarfile import TarFile
from urllib.request import urlopen

from . import botcmd, PY2
from .backends.base import Backend, ACLViolation
from .utils import (human_name_for_git_url,
                    which,
                    get_sender_username,
                    get_class_that_defined_method)
from .repos import KNOWN_PUBLIC_REPOS
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

    def __hash__(self):
        # Ensures this class (and subclasses) are hashable.
        # Presumably the use of mixins causes __hash__ to be
        # None otherwise.
        return int(id(self))

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

    # Repo management
    def get_installed_plugin_repos(self):
        return self.get(self.REPOS, {})

    def add_plugin_repo(self, name, url):
        if PY2:
            name = name.encode('utf-8')
            url = url.encode('utf-8')
        repos = self.get_installed_plugin_repos()
        repos[name] = url
        self[self.REPOS] = repos

    # plugin blacklisting management
    def get_blacklisted_plugin(self):
        return self.get(self.BL_PLUGINS, [])

    def is_plugin_blacklisted(self, name):
        return name in self.get_blacklisted_plugin()

    def blacklist_plugin(self, name):
        if self.is_plugin_blacklisted(name):
            logging.warning('Plugin %s is already blacklisted' % name)
            return 'Plugin %s is already blacklisted' % name
        self[self.BL_PLUGINS] = self.get_blacklisted_plugin() + [name]
        log.info('Plugin %s is now blacklisted' % name)
        return 'Plugin %s is now blacklisted' % name

    def unblacklist_plugin(self, name):
        if not self.is_plugin_blacklisted(name):
            logging.warning('Plugin %s is not blacklisted' % name)
            return 'Plugin %s is not blacklisted' % name
        l = self.get_blacklisted_plugin()
        l.remove(name)
        self[self.BL_PLUGINS] = l
        log.info('Plugin %s removed from blacklist' % name)
        return 'Plugin %s removed from blacklist' % name

    # configurations management
    def get_plugin_configuration(self, name):
        configs = self[self.CONFIGS]
        if name not in configs:
            return None
        return configs[name]

    def set_plugin_configuration(self, name, obj):
        configs = self[self.CONFIGS]
        configs[name] = obj
        self[self.CONFIGS] = configs

    # this will load the plugins the admin has setup at runtime
    def update_dynamic_plugins(self):
        all_candidates, errors = self.update_plugin_places(
            [self.plugin_dir + os.sep + d for d in self.get(self.REPOS, {}).keys()],
            self.bot_config.BOT_EXTRA_PLUGIN_DIR, self.bot_config.AUTOINSTALL_DEPS)
        self.all_candidates = all_candidates
        return errors

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

    def activate_non_started_plugins(self):
        log.info('Activating all the plugins...')
        configs = self[self.CONFIGS]
        errors = ''
        for pluginInfo in self.getAllPlugins():
            try:
                if self.is_plugin_blacklisted(pluginInfo.name):
                    errors += ('Notice: %s is blacklisted, use ' + self.prefix + 'load %s to unblacklist it\n') % (
                        pluginInfo.name, pluginInfo.name)
                    continue
                if hasattr(pluginInfo, 'is_activated') and not pluginInfo.is_activated:
                    log.info('Activate plugin: %s' % pluginInfo.name)
                    self.activate_plugin_with_version_check(pluginInfo.name, configs.get(pluginInfo.name, None))
            except Exception as e:
                log.exception("Error loading %s" % pluginInfo.name)
                errors += 'Error: %s failed to start : %s\n' % (pluginInfo.name, e)
        if errors:
            self.warn_admins(errors)
        return errors

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

    def shutdown(self):
        log.info('Shutdown.')
        self.close_storage()
        log.info('Bye.')

    def activate_plugin(self, name):
        try:
            if name in self.get_all_active_plugin_names():
                return "Plugin already in active list"
            if name not in self.get_all_plugin_names():
                return "I don't know this %s plugin" % name
            self.activate_plugin_with_version_check(name, self.get_plugin_configuration(name))
        except Exception as e:
            log.exception("Error loading %s" % name)
            return '%s failed to start : %s\n' % (name, e)
        self.get_plugin_obj_by_name(name).callback_connect()
        return "Plugin %s activated" % name

    def deactivate_plugin(self, name):
        if name not in self.get_all_active_plugin_names():
            return "Plugin %s not in active list" % name
        self.deactivate_plugin_by_name(name)
        return "Plugin %s deactivated" % name

    def install_repo(self, repo):
        if repo in KNOWN_PUBLIC_REPOS:
            repo = KNOWN_PUBLIC_REPOS[repo][0]  # replace it by the url
        git_path = which('git')

        if not git_path:
            return ('git command not found: You need to have git installed on '
                    'your system to be able to install git based plugins.', )

        if repo.endswith('tar.gz'):
            tar = TarFile(fileobj=urlopen(repo))
            tar.extractall(path=self.plugin_dir)
            human_name = args.split('/')[-1][:-7]
        else:
            human_name = human_name_for_git_url(repo)
            p = subprocess.Popen([git_path, 'clone', repo, human_name], cwd=self.plugin_dir, stdout=subprocess.PIPE,
                                 stderr=subprocess.PIPE)
            feedback = p.stdout.read().decode('utf-8')
            error_feedback = p.stderr.read().decode('utf-8')
            if p.wait():
                return ("Could not load this plugin : \n%s\n---\n%s" % (feedback, error_feedback), )
        self.add_plugin_repo(human_name, repo)
        return self.update_dynamic_plugins()

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
