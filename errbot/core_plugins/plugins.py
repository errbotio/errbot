# -*- coding: utf-8 -*-
from ast import literal_eval
import subprocess
from os import path
from pprint import pformat
import shutil

from errbot import BotPlugin, botcmd
from errbot.repos import KNOWN_PUBLIC_REPOS
from errbot.rendering import md_escape
from errbot.utils import which
from errbot.plugin_manager import check_dependencies, global_restart, PluginConfigurationException


class Plugins(BotPlugin):

    @botcmd(admin_only=True)
    def repos_install(self, mess, args):
        """ install a plugin repository from the given source or a known public repo (see !repos to find those).
        for example from a known repo : !install err-codebot
        for example a git url : git@github.com:gbin/plugin.git
        or an url towards a tar.gz archive : http://www.gootz.net/plugin-latest.tar.gz
        """
        if not args.strip():
            return "You should have an urls/git repo argument"
        errors = self._bot.install_repo(args)
        if errors:
            self.send(mess.frm, 'Some plugins are generating errors:\n' + '\n'.join(errors),
                      message_type=mess.type)
        else:
            self.send(
                mess.frm,
                ("A new plugin repository has been installed correctly from "
                 "%s. Refreshing the plugins commands..." % args),
                message_type=mess.type
            )
        loading_errors = self._bot.activate_non_started_plugins()
        if loading_errors:
            return loading_errors
        return "Plugins reloaded without any error."

    @botcmd(admin_only=True)
    def repos_uninstall(self, mess, args):
        """ uninstall a plugin repository by name.
        """
        if not args.strip():
            return "You should have a repo name as argument"
        repos = self._bot.get(self._bot.REPOS, {})
        if args not in repos:
            return "This repo is not installed check with " + self._bot.prefix + "repos the list of installed ones"

        plugin_path = path.join(self._bot.plugin_dir, args)
        for plugin in self._bot.getAllPlugins():
            if plugin.path.startswith(plugin_path) and hasattr(plugin, 'is_activated') and plugin.is_activated:
                self.send(mess.frm, '/me is unloading plugin %s' % plugin.name)
                self._bot.deactivate_plugin(plugin.name)

        shutil.rmtree(plugin_path)
        repos.pop(args)
        self[self._bot.REPOS] = repos

        return 'Plugins unloaded and repo %s removed' % args

    # noinspection PyUnusedLocal
    @botcmd(template='repos')
    def repos(self, mess, args):
        """ list the current active plugin repositories
        """
        installed_repos = self._bot.get_installed_plugin_repos()
        all_names = sorted(set([name for name in KNOWN_PUBLIC_REPOS] + [name for name in installed_repos]))
        return {'repos': [
            (repo_name in installed_repos, repo_name in KNOWN_PUBLIC_REPOS, repo_name,
             KNOWN_PUBLIC_REPOS[repo_name][1]
             if repo_name in KNOWN_PUBLIC_REPOS else installed_repos[repo_name])
            for repo_name in all_names]}

    @botcmd(split_args_with=' ', admin_only=True)
    def repos_update(self, mess, args):
        """ update the bot and/or plugins
        use : !repos update all
        to update everything
        or : !repos update core
        to update only the core
        or : !repos update repo_name repo_name ...
        to update selectively some repos
        """
        git_path = which('git')
        if not git_path:
            return ('git command not found: You need to have git installed on '
                    'your system to be able to install git based plugins.')

        directories = set()
        repos = self._bot.get(self._bot.REPOS, {})
        core_to_update = 'all' in args or 'core' in args
        if core_to_update:
            directories.add(path.dirname(__file__))

        if 'all' in args:
            directories.update([path.join(self._bot.plugin_dir, name) for name in repos])
        else:
            directories.update([path.join(self._bot.plugin_dir, name) for name in set(args).intersection(set(repos))])

        for d in directories:
            self.send(mess.frm, "I am updating %s ..." % d, message_type=mess.type)
            p = subprocess.Popen([git_path, 'pull'], cwd=d, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            feedback = p.stdout.read().decode('utf-8') + '\n' + '-' * 50 + '\n'
            err = p.stderr.read().strip().decode('utf-8')
            if err:
                feedback += err + '\n' + '-' * 50 + '\n'
            dep_err = check_dependencies(d)
            if dep_err:
                feedback += dep_err + '\n'
            if p.wait():
                self.send(mess.frm, "Update of %s failed...\n\n%s\n\n resuming..." % (d, feedback),
                          message_type=mess.type)
            else:
                self.send(mess.frm, "Update of %s succeeded...\n\n%s\n\n" % (d, feedback),
                          message_type=mess.type)
                if not core_to_update:
                    for plugin in self._bot.getAllPlugins():
                        if plugin.path.startswith(d) and hasattr(plugin, 'is_activated') and plugin.is_activated:
                            name = plugin.name
                            self.send(mess.frm, '/me is reloading plugin %s' % name)
                            self._bot.reload_plugin_by_name(plugin.name)
                            self.send(mess.frm, '%s reloaded and reactivated' % name)
        if core_to_update:
            self.send(mess.frm, "You have updated the core, I need to restart.", message_type=mess.type)
            global_restart()
        return "Done."

    # noinspection PyUnusedLocal
    @botcmd(split_args_with=' ', admin_only=True)
    def plugin_config(self, mess, args):
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
        if self._bot.is_plugin_blacklisted(plugin_name):
            return 'Load this plugin first with ' + self._bot.prefix + 'load %s' % plugin_name
        obj = self._bot.get_plugin_obj_by_name(plugin_name)
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

            current_config = self._bot.get_plugin_configuration(plugin_name)
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

        self._bot.set_plugin_configuration(plugin_name, real_config_obj)
        self._bot.deactivate_plugin(plugin_name)
        try:
            self._bot.activate_plugin(plugin_name)
        except PluginConfigurationException as ce:
            self.log.debug('Invalid configuration for the plugin, reverting the plugin to unconfigured')
            self._bot.set_plugin_configuration(plugin_name, None)
            return 'Incorrect plugin configuration: %s' % ce
        return 'Plugin configuration done.'

    def formatted_plugin_list(self, active_only=True):
        """
        Return a formatted, plain-text list of loaded plugins.

        When active_only=True, this will only return plugins which
        are actually active. Otherwise, it will also include inactive
        (blacklisted) plugins.
        """
        if active_only:
            all_plugins = self._bot.get_all_active_plugin_names()
        else:
            all_plugins = self._bot.get_all_plugin_names()
        return "\n".join(("- " + plugin for plugin in all_plugins))

    # noinspection PyUnusedLocal
    @botcmd(admin_only=True)
    def plugin_reload(self, mess, args):
        """reload a plugin: reload the code of the plugin leaving the activation status intact."""
        name = args.strip()
        if not name:
            yield ("Please tell me which of the following plugins to reload:\n"
                   "{}".format(self.formatted_plugin_list(active_only=False)))
            return
        if name not in self._bot.get_all_plugin_names():
            yield ("{} isn't a valid plugin name. The current plugins are:\n"
                   "{}".format(name, self.formatted_plugin_list(active_only=False)))
            return

        if name not in self._bot.get_all_active_plugin_names():
            yield (("Warning: plugin %s is currently not activated. " +
                   "Use !plugin activate %s to activate it.") % (name, name))

        self._bot.reload_plugin_by_name(name)

        yield "Plugin %s reloaded." % name

    # noinspection PyUnusedLocal
    @botcmd(admin_only=True)
    def plugin_activate(self, mess, args):
        """activate a plugin. [calls .activate() on the plugin]"""
        args = args.strip()
        if not args:
            return ("Please tell me which of the following plugins to activate:\n"
                    "{}".format(self.formatted_plugin_list(active_only=False)))
        if args not in self._bot.get_all_plugin_names():
            return ("{} isn't a valid plugin name. The current plugins are:\n"
                    "{}".format(args, self.formatted_plugin_list(active_only=False)))
        if args in self._bot.get_all_active_plugin_names():
            return "{} is already activated.".format(args)

        return self._bot.activate_plugin(args)

    # noinspection PyUnusedLocal
    @botcmd(admin_only=True)
    def plugin_deactivate(self, mess, args):
        """deactivate a plugin. [calls .deactivate on the plugin]"""
        args = args.strip()
        if not args:
            return ("Please tell me which of the following plugins to deactivate:\n"
                    "{}".format(self.formatted_plugin_list(active_only=False)))
        if args not in self._bot.get_all_plugin_names():
            return ("{} isn't a valid plugin name. The current plugins are:\n"
                    "{}".format(args, self.formatted_plugin_list(active_only=False)))
        if args not in self._bot.get_all_active_plugin_names():
            return "{} is already deactivated.".format(args)

        return self._bot.deactivate_plugin(args)

    # noinspection PyUnusedLocal
    @botcmd(admin_only=True)
    def plugin_blacklist(self, mess, args):
        """Blacklist a plugin so that it will not be loaded automatically during bot startup.
        If the plugin is currently activated, it will deactiveate it first."""
        if args not in self._bot.get_all_plugin_names():
            return ("{} isn't a valid plugin name. The current plugins are:\n"
                    "{}".format(args, self.formatted_plugin_list(active_only=False)))

        if args in self._bot.get_all_active_plugin_names():
            self._bot.deactivate_plugin(args)

        return self._bot.blacklist_plugin(args)

    # noinspection PyUnusedLocal
    @botcmd(admin_only=True)
    def plugin_unblacklist(self, mess, args):
        """Remove a plugin from the blacklist"""
        if args not in self._bot.get_all_plugin_names():
            return ("{} isn't a valid plugin name. The current plugins are:\n"
                    "{}".format(args, self.formatted_plugin_list(active_only=False)))

        if args not in self._bot.get_all_active_plugin_names():
            self._bot.activate_plugin(args)

        return self._bot.unblacklist_plugin(args)
