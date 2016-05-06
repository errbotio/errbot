# -*- coding: utf-8 -*-
from ast import literal_eval
from pprint import pformat
import os
import shutil

from errbot import BotPlugin, botcmd
from errbot.plugin_manager import PluginConfigurationException, PluginActivationException
from errbot.repo_manager import RepoException


class Plugins(BotPlugin):

    @botcmd(admin_only=True)
    def repos_install(self, mess, args):
        """ install a plugin repository from the given source or a known public repo (see !repos to find those).
        for example from a known repo : !install err-codebot
        for example a git url : git@github.com:gbin/plugin.git
        or an url towards a tar.gz archive : http://www.gootz.net/plugin-latest.tar.gz
        """
        args = args.strip()
        if not args:
            yield "Please specify a repository listed in '!repos' or " \
                  "give me the URL to a git repository that I should clone for you."
            return
        try:
            yield "Installing %s..." % args
            local_path = self._bot.repo_manager.install_repo(args)
            errors = self._bot.plugin_manager.update_dynamic_plugins()
            if errors:
                yield 'Some plugins are generating errors:\n' + '\n'.join(errors.values())
                # if the load of the plugin failed, uninstall cleanly teh repo
                for path in errors.keys():
                    if path.startswith(local_path):
                        yield 'Removing %s as it did not load correctly.' % local_path
                        shutil.rmtree(local_path)
            else:
                yield ("A new plugin repository has been installed correctly from "
                       "%s. Refreshing the plugins commands..." % args)
            loading_errors = self._bot.plugin_manager.activate_non_started_plugins()
            if loading_errors:
                yield loading_errors
            yield "Plugins reloaded."
        except RepoException as re:
            yield "Error installing the repo: %s" % re

    @botcmd(admin_only=True)
    def repos_uninstall(self, _, repo_name):
        """ uninstall a plugin repository by name.
        """
        if not repo_name.strip():
            yield "You should have a repo name as argument"
            return

        repos = self._bot.repo_manager.get_installed_plugin_repos()

        if repo_name not in repos:
            yield "This repo is not installed check with " + self._bot.prefix + "repos the list of installed ones"
            return

        plugin_path = os.path.join(self._bot.repo_manager.plugin_dir, repo_name)
        self._bot.plugin_manager.remove_plugins_from_path(plugin_path)
        self._bot.repo_manager.uninstall_repo(repo_name)
        yield 'Repo %s removed.' % repo_name

    @botcmd(template='repos')
    def repos(self, _, args):
        """ list the current active plugin repositories
        """

        installed_repos = self._bot.repo_manager.get_installed_plugin_repos()

        all_names = [name for name in installed_repos]

        repos = {'repos': []}

        for repo_name in all_names:

            installed = False

            if repo_name in installed_repos:
                installed = True

            from_index = self._bot.repo_manager.get_repo_from_index(repo_name)

            if from_index is not None:
                description = '\n'.join(('%s: %s' % (plug.name, plug.documentation) for plug in from_index))
            else:
                description = 'No description.'

            # installed, public, name, desc
            repos['repos'].append((installed, from_index is not None, repo_name, description))

        return repos

    @botcmd(template='repos2')
    def repos_search(self, _, args):
        """ Searches the repo index.
        for example: !repos search jenkins
        """
        if not args:
            # TODO(gbin): return all the repos.
            return {'error': "Please specify a keyword."}
        return {'repos': self._bot.repo_manager.search_repos(args)}

    @botcmd(split_args_with=' ', admin_only=True)
    def repos_update(self, _, args):
        """ update the bot and/or plugins
        use : !repos update all
        to update everything
        or : !repos update repo_name repo_name ...
        to update selectively some repos
        """
        if 'all' in args:
            results = self._bot.repo_manager.update_all_repos()
        else:
            results = self._bot.repo_manager.update_repos(args)

        yield "Start updating ... "

        for d, success, feedback in results:
            if success:
                yield "Update of %s succeeded...\n\n%s\n\n" % (d, feedback)
            else:
                yield "Update of %s failed...\n\n%s" % (d, feedback)

            for plugin in self._bot.plugin_manager.getAllPlugins():
                if plugin.path.startswith(d) and hasattr(plugin, 'is_activated') and plugin.is_activated:
                    name = plugin.name
                    yield '/me is reloading plugin %s' % name
                    try:
                        self._bot.plugin_manager.reload_plugin_by_name(plugin.name)
                        yield "Plugin %s reloaded." % plugin.name
                    except PluginActivationException as pae:
                        yield 'Error reactivating plugin %s: %s' % (plugin.name, pae)
        yield "Done."

    @botcmd(split_args_with=' ', admin_only=True)
    def plugin_config(self, _, args):
        """ configure or get the configuration / configuration template for a specific plugin
        ie.
        !plugin config ExampleBot
        could return a template if it is not configured:
        {'LOGIN': 'example@example.com', 'PASSWORD': 'password', 'DIRECTORY': '/toto'}
        Copy paste, adapt so can configure the plugin :
        !plugin config ExampleBot {'LOGIN': 'my@email.com', 'PASSWORD': 'myrealpassword', 'DIRECTORY': '/tmp'}
        It will then reload the plugin with this config.
        You can at any moment retreive the current values:
        !plugin config ExampleBot
        should return :
        {'LOGIN': 'my@email.com', 'PASSWORD': 'myrealpassword', 'DIRECTORY': '/tmp'}
        """
        plugin_name = args[0]
        if self._bot.plugin_manager.is_plugin_blacklisted(plugin_name):
            return 'Load this plugin first with ' + self._bot.prefix + 'load %s' % plugin_name
        obj = self._bot.plugin_manager.get_plugin_obj_by_name(plugin_name)
        if obj is None:
            return 'Unknown plugin or the plugin could not load %s' % plugin_name
        template_obj = obj.get_configuration_template()
        if template_obj is None:
            return 'This plugin is not configurable.'

        if len(args) == 1:
            response = ("Default configuration for this plugin (you can copy and paste "
                        "this directly as a command):\n\n"
                        "```\n{prefix}plugin config {plugin_name} \n{config}\n```").format(
                prefix=self._bot.prefix, plugin_name=plugin_name, config=pformat(template_obj))

            current_config = self._bot.plugin_manager.get_plugin_configuration(plugin_name)
            if current_config:
                response += ("\n\nCurrent configuration:\n\n"
                             "```\n{prefix}plugin config {plugin_name} \n{config}\n```").format(
                    prefix=self._bot.prefix, plugin_name=plugin_name, config=pformat(current_config))
            return response

        # noinspection PyBroadException
        try:
            real_config_obj = literal_eval(' '.join(args[1:]))
        except Exception:
            self.log.exception('Invalid expression for the configuration of the plugin')
            return 'Syntax error in the given configuration'
        if type(real_config_obj) != type(template_obj):
            return 'It looks fishy, your config type is not the same as the template !'

        self._bot.plugin_manager.set_plugin_configuration(plugin_name, real_config_obj)

        try:
            self._bot.plugin_manager.deactivate_plugin(plugin_name)
        except PluginActivationException as pae:
            return 'Error deactivating %s: %s' % (plugin_name, pae)

        try:
            self._bot.plugin_manager.activate_plugin(plugin_name)
        except PluginConfigurationException as ce:
            self.log.debug('Invalid configuration for the plugin, reverting the plugin to unconfigured.')
            self._bot.plugin_manager.set_plugin_configuration(plugin_name, None)
            return 'Incorrect plugin configuration: %s' % ce
        except PluginActivationException as pae:
            return 'Error activating plugin: %s' % pae

        return 'Plugin configuration done.'

    def formatted_plugin_list(self, active_only=True):
        """
        Return a formatted, plain-text list of loaded plugins.

        When active_only=True, this will only return plugins which
        are actually active. Otherwise, it will also include inactive
        (blacklisted) plugins.
        """
        if active_only:
            all_plugins = self._bot.plugin_manager.get_all_active_plugin_names()
        else:
            all_plugins = self._bot.plugin_manager.get_all_plugin_names()
        return "\n".join(("- " + plugin for plugin in all_plugins))

    @botcmd(admin_only=True)
    def plugin_reload(self, _, args):
        """reload a plugin: reload the code of the plugin leaving the activation status intact."""
        name = args.strip()
        if not name:
            yield ("Please tell me which of the following plugins to reload:\n"
                   "{}".format(self.formatted_plugin_list(active_only=False)))
            return
        if name not in self._bot.plugin_manager.get_all_plugin_names():
            yield ("{} isn't a valid plugin name. The current plugins are:\n"
                   "{}".format(name, self.formatted_plugin_list(active_only=False)))
            return

        if name not in self._bot.plugin_manager.get_all_active_plugin_names():
            yield (("Warning: plugin %s is currently not activated. " +
                   "Use `%splugin activate %s` to activate it.") % (name, self._bot.prefix, name))

        try:
            self._bot.plugin_manager.reload_plugin_by_name(name)
            yield "Plugin %s reloaded." % name
        except PluginActivationException as pae:
            yield 'Error activating plugin %s: %s' % (name, pae)

    @botcmd(admin_only=True)
    def plugin_activate(self, _, args):
        """activate a plugin. [calls .activate() on the plugin]"""
        args = args.strip()
        if not args:
            return ("Please tell me which of the following plugins to activate:\n"
                    "{}".format(self.formatted_plugin_list(active_only=False)))
        if args not in self._bot.plugin_manager.get_all_plugin_names():
            return ("{} isn't a valid plugin name. The current plugins are:\n"
                    "{}".format(args, self.formatted_plugin_list(active_only=False)))
        if args in self._bot.plugin_manager.get_all_active_plugin_names():
            return "{} is already activated.".format(args)

        try:
            self._bot.plugin_manager.activate_plugin(args)
        except PluginActivationException as pae:
            return 'Error activating plugin: %s' % pae
        return 'Plugin {} activated.'.format(args)

    @botcmd(admin_only=True)
    def plugin_deactivate(self, _, args):
        """deactivate a plugin. [calls .deactivate on the plugin]"""
        args = args.strip()
        if not args:
            return ("Please tell me which of the following plugins to deactivate:\n"
                    "{}".format(self.formatted_plugin_list(active_only=False)))
        if args not in self._bot.plugin_manager.get_all_plugin_names():
            return ("{} isn't a valid plugin name. The current plugins are:\n"
                    "{}".format(args, self.formatted_plugin_list(active_only=False)))
        if args not in self._bot.plugin_manager.get_all_active_plugin_names():
            return "{} is already deactivated.".format(args)

        try:
            self._bot.plugin_manager.deactivate_plugin(args)
        except PluginActivationException as pae:
            return 'Error deactivating %s: %s' % (args, pae)
        return 'Plugin {} deactivated.'.format(args)

    @botcmd(admin_only=True)
    def plugin_blacklist(self, _, args):
        """Blacklist a plugin so that it will not be loaded automatically during bot startup.
        If the plugin is currently activated, it will deactiveate it first."""
        if args not in self._bot.plugin_manager.get_all_plugin_names():
            return ("{} isn't a valid plugin name. The current plugins are:\n"
                    "{}".format(args, self.formatted_plugin_list(active_only=False)))

        if args in self._bot.plugin_manager.get_all_active_plugin_names():
            try:
                self._bot.plugin_manager.deactivate_plugin(args)
            except PluginActivationException as pae:
                return 'Error deactivating %s: %s' % (args, pae)
        return self._bot.plugin_manager.blacklist_plugin(args)

    @botcmd(admin_only=True)
    def plugin_unblacklist(self, _, args):
        """Remove a plugin from the blacklist"""
        if args not in self._bot.plugin_manager.get_all_plugin_names():
            return ("{} isn't a valid plugin name. The current plugins are:\n"
                    "{}".format(args, self.formatted_plugin_list(active_only=False)))

        if args not in self._bot.plugin_manager.get_all_active_plugin_names():
            try:
                self._bot.plugin_manager.activate_plugin(args)
            except PluginActivationException as pae:
                return 'Error activating plugin: %s' % pae

        return self._bot.plugin_manager.unblacklist_plugin(args)
