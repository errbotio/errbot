from ast import literal_eval
from pprint import pformat
import os
import shutil
import logging

from errbot import BotPlugin, botcmd
from errbot.plugin_manager import PluginConfigurationException, PluginActivationException
from errbot.repo_manager import RepoException


class Plugins(BotPlugin):

    @botcmd(admin_only=True)
    def repos_install(self, _, args):
        """ install a plugin repository from the given source or a known public repo (see !repos to find those).
        for example from a known repo : !install err-codebot
        for example a git url : git@github.com:gbin/plugin.git
        or an url towards a tar.gz archive : http://www.gootz.net/plugin-latest.tar.gz
        """
        args = args.strip()
        if not args:
            yield 'Please specify a repository listed in "!repos" or ' \
                  'give me the URL to a git repository that I should clone for you.'
            return
        try:
            yield f'Installing {args}...'
            local_path = self._bot.repo_manager.install_repo(args)
            errors = self._bot.plugin_manager.update_plugin_places(self._bot.repo_manager.get_all_repos_paths())
            if errors:
                v = '\n'.join(errors.values())
                yield f'Some plugins are generating errors:\n{v}.'
                # if the load of the plugin failed, uninstall cleanly teh repo
                for path in errors.keys():
                    if str(path).startswith(local_path):
                        yield f'Removing {local_path} as it did not load correctly.'
                        shutil.rmtree(local_path)
            else:
                yield f'A new plugin repository has been installed correctly from {args}. ' \
                      f'Refreshing the plugins commands...'
            loading_errors = self._bot.plugin_manager.activate_non_started_plugins()
            if loading_errors:
                yield loading_errors
            yield 'Plugins reloaded.'
        except RepoException as re:
            yield f'Error installing the repo: {re}'

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
        yield f'Repo {repo_name} removed.'

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
                description = '\n'.join((f'{plug.name}: {plug.documentation}' for plug in from_index))
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
                yield f'Update of {d} succeeded...\n\n{feedback}\n\n'

                plugin = self._bot.plugin_manager.get_plugin_by_path(d)
                if hasattr(plugin, 'is_activated') and plugin.is_activated:
                    name = plugin.name
                    yield f'/me is reloading plugin {name}'
                    try:
                        self._bot.plugin_manager.reload_plugin_by_name(plugin.name)
                        yield f'Plugin {plugin.name} reloaded.'
                    except PluginActivationException as pae:
                        yield f'Error reactivating plugin {plugin.name}: {pae}'
            else:
                yield f'Update of {d} failed...\n\n{feedback}'

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
        You can at any moment retrieve the current values:
        !plugin config ExampleBot
        should return :
        {'LOGIN': 'my@email.com', 'PASSWORD': 'myrealpassword', 'DIRECTORY': '/tmp'}
        """
        plugin_name = args[0]
        if self._bot.plugin_manager.is_plugin_blacklisted(plugin_name):
            return f'Load this plugin first with {self._bot.prefix} load {plugin_name}.'
        obj = self._bot.plugin_manager.get_plugin_obj_by_name(plugin_name)
        if obj is None:
            return f'Unknown plugin or the plugin could not load {plugin_name}.'
        template_obj = obj.get_configuration_template()
        if template_obj is None:
            return 'This plugin is not configurable.'

        if len(args) == 1:
            response = f'Default configuration for this plugin (you can copy and paste this directly as a command):' \
                       f'\n\n```\n{self._bot.prefix}plugin config {plugin_name} {pformat(template_obj)}\n```'

            current_config = self._bot.plugin_manager.get_plugin_configuration(plugin_name)
            if current_config:
                response += f'\n\nCurrent configuration:\n\n```\n{self._bot.prefix}plugin config {plugin_name} ' \
                            f'{pformat(current_config)}\n```'
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
            return f'Error deactivating {plugin_name}: {pae}.'

        try:
            self._bot.plugin_manager.activate_plugin(plugin_name)
        except PluginConfigurationException as ce:
            self.log.debug('Invalid configuration for the plugin, reverting the plugin to unconfigured.')
            self._bot.plugin_manager.set_plugin_configuration(plugin_name, None)
            return f'Incorrect plugin configuration: {ce}.'
        except PluginActivationException as pae:
            return f'Error activating plugin: {pae}.'

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
            yield (
                f'Please tell me which of the following plugins to reload:\n'
                f'{self.formatted_plugin_list(active_only=False)}')
            return
        if name not in self._bot.plugin_manager.get_all_plugin_names():
            yield (f'{name} isn\'t a valid plugin name. '
                   f'The current plugins are:\n{self.formatted_plugin_list(active_only=False)}')
            return

        if name not in self._bot.plugin_manager.get_all_active_plugin_names():
            answer = f'Warning: plugin {name} is currently not activated. '
            answer += f'Use `{self._bot.prefix}plugin activate {name}` to activate it.'
            yield answer

        try:
            self._bot.plugin_manager.reload_plugin_by_name(name)
            yield f'Plugin {name} reloaded.'
        except PluginActivationException as pae:
            yield f'Error activating plugin {name}: {pae}.'

    @botcmd(admin_only=True)
    def plugin_activate(self, _, args):
        """activate a plugin. [calls .activate() on the plugin]"""
        args = args.strip()
        if not args:
            return (f'Please tell me which of the following plugins to activate:\n'
                    f'{self.formatted_plugin_list(active_only=False)}')
        if args not in self._bot.plugin_manager.get_all_plugin_names():
            return (f"{args} isn't a valid plugin name. The current plugins are:\n"
                    f"{self.formatted_plugin_list(active_only=False)}")
        if args in self._bot.plugin_manager.get_all_active_plugin_names():
            return f'{args} is already activated.'

        try:
            self._bot.plugin_manager.activate_plugin(args)
        except PluginActivationException as pae:
            return f'Error activating plugin: {pae}'
        return f'Plugin {args} activated.'

    @botcmd(admin_only=True)
    def plugin_deactivate(self, _, args):
        """deactivate a plugin. [calls .deactivate on the plugin]"""
        args = args.strip()
        if not args:
            return (f'Please tell me which of the following plugins to deactivate:\n'
                    f'{self.formatted_plugin_list(active_only=False)}')
        if args not in self._bot.plugin_manager.get_all_plugin_names():
            return (f"{args} isn't a valid plugin name. The current plugins are:\n"
                    f"{self.formatted_plugin_list(active_only=False)}")
        if args not in self._bot.plugin_manager.get_all_active_plugin_names():
            return f'{args} is already deactivated.'

        try:
            self._bot.plugin_manager.deactivate_plugin(args)
        except PluginActivationException as pae:
            return f'Error deactivating {args}: {pae}'
        return f'Plugin {args} deactivated.'

    @botcmd(admin_only=True)
    def plugin_blacklist(self, _, args):
        """Blacklist a plugin so that it will not be loaded automatically during bot startup.
        If the plugin is currently activated, it will deactiveate it first."""
        if args not in self._bot.plugin_manager.get_all_plugin_names():
            return (f"{args} isn't a valid plugin name. The current plugins are:\n"
                    f"{self.formatted_plugin_list(active_only=False)}")

        if args in self._bot.plugin_manager.get_all_active_plugin_names():
            try:
                self._bot.plugin_manager.deactivate_plugin(args)
            except PluginActivationException as pae:
                return f'Error deactivating {args}: {pae}.'
        return self._bot.plugin_manager.blacklist_plugin(args)

    @botcmd(admin_only=True)
    def plugin_unblacklist(self, _, args):
        """Remove a plugin from the blacklist"""
        if args not in self._bot.plugin_manager.get_all_plugin_names():
            return (f"{args} isn't a valid plugin name. The current plugins are:\n"
                    f"{self.formatted_plugin_list(active_only=False)}")

        if args not in self._bot.plugin_manager.get_all_active_plugin_names():
            try:
                self._bot.plugin_manager.activate_plugin(args)
            except PluginActivationException as pae:
                return f'Error activating plugin: {pae}'

        return self._bot.plugin_manager.unblacklist_plugin(args)

    @botcmd(admin_only=True, template='plugin_info')
    def plugin_info(self, _, args):
        """Gives you a more technical information about a specific plugin."""
        pm = self._bot.plugin_manager
        if args not in pm.get_all_plugin_names():
            return (f"{args} isn't a valid plugin name. The current plugins are:\n"
                    f"{self.formatted_plugin_list(active_only=False)}")
        return {'plugin_info': pm.plugin_infos[args],
                'plugin': pm.plugins[args],
                'logging': logging}
