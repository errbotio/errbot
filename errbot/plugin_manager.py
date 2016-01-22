""" Logic related to plugin loading and lifecycle """

from configparser import NoSectionError, NoOptionError, ConfigParser
from itertools import chain
import importlib
import imp
import inspect
import logging
import sys
import os
import subprocess
from tarfile import TarFile
from urllib.request import urlopen

import pip
from .botplugin import BotPlugin
from .utils import (version2array, PY3, PY2, find_roots_with_extra,
                    which, human_name_for_git_url)
from .templating import remove_plugin_templates_path, add_plugin_templates_path
from .version import VERSION
from yapsy.PluginManager import PluginManager
from yapsy.PluginFileLocator import PluginFileLocator, PluginFileAnalyzerWithInfoFile
from .core_plugins.wsview import route
from .storage import StoreMixin
from .repos import KNOWN_PUBLIC_REPOS

log = logging.getLogger(__name__)

CORE_PLUGINS = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                            'core_plugins')

try:
    from importlib import reload  # new in python 3.4
except ImportError:
    from imp import reload  # noqa


class IncompatiblePluginException(Exception):
    pass


class PluginConfigurationException(Exception):
    pass


def populate_doc(plugin):
    plugin_type = type(plugin.plugin_object)
    plugin_type.__errdoc__ = plugin_type.__doc__ if plugin_type.__doc__ else plugin.description


def install_package(package):
    log.info("Installing package '%s'." % package)
    if hasattr(sys, 'real_prefix'):
        # this is a virtualenv, so we can use it directly
        pip.main(['install', package])
    else:
        # otherwise only install it as a user package
        pip.main(['install', '--user', package])
    try:
        globals()[package] = importlib.import_module(package)
    except:
        log.exception("Failed to load the dependent package")


def check_dependencies(path):
    """ This methods returns a pair of (message, packages missing).
    Or None if everything is OK.
    """
    log.debug("check dependencies of %s" % path)
    # noinspection PyBroadException
    try:
        from pkg_resources import get_distribution

        req_path = path + os.sep + 'requirements.txt'
        if not os.path.isfile(req_path):
            log.debug('%s has no requirements.txt file' % path)
            return None
        missing_pkg = []
        with open(req_path) as f:
            for line in f:
                stripped = line.strip()
                # noinspection PyBroadException
                try:
                    get_distribution(stripped)
                except Exception:
                    missing_pkg.append(stripped)
        if missing_pkg:
            return (('You need those dependencies for %s: ' % path) + ','.join(missing_pkg),
                    missing_pkg)
        return None
    except Exception:
        return 'You need to have setuptools installed for the dependency check of the plugins', []


def check_enabled_core_plugin(name: str, config: ConfigParser, core_plugin_list) -> bool:
    """ Checks if the given plugin is core and if it is, if it is part of the enabled core_plugins_list.

    :param name: The plugin name
    :param config: Its config
    :param core_plugin_list: the list from CORE_PLUGINS in the config.
    :return: True if it is OK to load this plugin.
    """
    try:
        core = config.get("Core", "Core")
        if core.lower() == 'true' and name not in core_plugin_list:
            return False
    except NoOptionError:
        pass
    return True


def check_python_plug_section(name: str, config: ConfigParser) -> bool:
    """ Checks if we have the correct version to run this plugin.
    Returns true if the plugin is loadable """
    try:
        python_version = config.get("Python", "Version")
    except NoSectionError:
        log.warning(
            'Plugin %s has no section [Python]. Assuming this '
            'plugin is runnning only under python 2.', name)
        python_version = '2'

    if python_version not in ('2', '2+', '3'):
        log.warning(
            'Plugin %s has an invalid Version specified in section [Python]. '
            'The Version can only be 2, 2+ and 3', name)
        return False

    if python_version == '2' and PY3:
        log.error(
            '\nPlugin %s is made for python 2 only and you are running '
            'err under python 3.\n\n'
            'If the plugin can be run on python 2 and 3 please add this '
            'section to its .plug descriptor :\n[Python]\nVersion=2+\n\n'
            'Or if the plugin is Python 3 only:\n[Python]\nVersion=3\n\n', name)
        return False

    if python_version == '3' and PY2:
        log.error('\nPlugin %s is made for python 3 and you are running err under python 2.')
        return False
    return True


def check_errbot_version(name: str, min_version: str, max_version: str):
    """ Checks if a plugin version between min_version and max_version is ok
    for this errbot.
    Raises IncompatiblePluginException if not.
    """
    log.info('Activating %s with min_err_version = %s and max_version = %s',
             name, min_version, max_version)
    current_version = version2array(VERSION)
    if min_version and version2array(min_version) > current_version:
        raise IncompatiblePluginException(
            'The plugin %s asks for err with a minimal version of %s while err is version %s' % (
                name, min_version, VERSION)
        )

    if max_version and version2array(max_version) < current_version:
        raise IncompatiblePluginException(
            'The plugin %s asks for err with a maximal version of %s while err is version %s' % (
                name, max_version, VERSION)
        )


def check_errbot_plug_section(name: str, config: ConfigParser) -> bool:
    """ Checks if we have the correct Errbot version.
    Returns true if the plugin is loadable """

    # Errbot version check
    try:

        try:
            min_version = config.get("Errbot", "Min")
        except NoOptionError:
            log.debug('Plugin %s has no Min Option in [Errbot] section. '
                      'Assuming this plugin is running on this Errbot'
                      'version as min version.', name)
            min_version = VERSION

        try:
            max_version = config.get("Errbot", "Max")
        except NoOptionError:
            log.debug('Plugin %s has no Max Option in [Errbot] section. '
                      'Assuming this plugin is running on this Errbot'
                      'version as max version.', name)
            max_version = VERSION

    except NoSectionError:
        log.debug('Plugin %s has no section [Errbot]. Assuming this '
                  'plugin is runnning on any Errbot version.', name)
        min_version = VERSION
        max_version = VERSION
    try:
        check_errbot_version(name, min_version, max_version)
    except IncompatiblePluginException as ex:
        log.error("Could not load plugin:\n%s", str(ex))
        return False
    return True


def global_restart():
    python = sys.executable
    os.execl(python, python, *sys.argv)


class BotPluginManager(PluginManager, StoreMixin):
    """Customized yapsy PluginManager for ErrBot."""

    # Storage names
    REPOS = b'repos' if PY2 else 'repos'
    CONFIGS = b'configs' if PY2 else 'configs'
    BL_PLUGINS = b'bl_plugins' if PY2 else 'bl_plugins'

    def __init__(self, storage_plugin, plugin_dir, extra, autoinstall_deps, core_plugins):
        self.bot = None
        self.autoinstall_deps = autoinstall_deps
        self.extra = extra
        self.open_storage(storage_plugin, 'core')
        self.plugin_dir = plugin_dir
        self.core_plugins = core_plugins

        # be sure we have a configs entry for the plugin configurations
        if self.CONFIGS not in self:
            self[self.CONFIGS] = {}

        locator = PluginFileLocator([PluginFileAnalyzerWithInfoFile("info_ext", 'plug')])
        locator.disableRecursiveScan()  # We do that ourselves
        super().__init__(categories_filter={"bots": BotPlugin}, plugin_locator=locator)

    def attach_bot(self, bot):
        self.bot = bot

    def instanciateElement(self, element):
        """ Override the loading method to inject bot """
        if PY3:
            # check if we have a plugin not overridding __init__ incorrectly
            sig = inspect.signature(element.__init__)

            log.debug('plugin __init__(%s)' % sig.parameters)
            if len(sig.parameters) == 1:
                log.warn(('Warning: %s needs to implement __init__(self, *args, **kwargs) '
                          'and forward them to super().__init__') % element.__name__)
                obj = element()
                obj._load_bot(self.bot)  # sideload the bot
                return obj

        return element(self.bot)

    def get_plugin_by_name(self, name):
        return self.getPluginByName(name, 'bots')

    def get_plugin_obj_by_name(self, name):
        plugin = self.get_plugin_by_name(name)
        return None if plugin is None else plugin.plugin_object

    def activate_plugin_with_version_check(self, name, config):
        pta_item = self.getPluginByName(name, 'bots')
        if pta_item is None:
            log.warning('Could not activate %s', name)
            return None

        if self.core_plugins is not None:
            if not check_enabled_core_plugin(name, pta_item.details, self.core_plugins):
                log.warn('Core plugin "%s" has been skipped because it is not in CORE_PLUGINS in config.py.' % name)
                return None

        if not check_python_plug_section(name, pta_item.details):
            log.error('%s failed python version check.', name)
            return None

        if not check_errbot_plug_section(name, pta_item.details):
            log.error('%s failed errbot version check.', name)
            return None

        obj = pta_item.plugin_object

        # Deprecated: old way to check for min/max versions
        check_errbot_version(name, obj.min_err_version, obj.max_err_version)

        try:
            if obj.get_configuration_template() is not None and config is not None:
                log.debug('Checking configuration for %s...', name)
                obj.check_configuration(config)
                log.debug('Configuration for %s checked OK.', name)
            obj.configure(config)  # even if it is None we pass it on
        except Exception as ex:
            log.exception('Something is wrong with the configuration of the plugin %s', name)
            obj.config = None
            raise PluginConfigurationException(str(ex))
        add_plugin_templates_path(pta_item.path)
        populate_doc(pta_item)
        try:
            obj = self.activatePluginByName(name, "bots")
            route(obj)
            return obj
        except Exception:
            pta_item.activated = False  # Yapsy doesn't revert this in case of error
            remove_plugin_templates_path(pta_item.path)
            log.error("Plugin %s failed at activation stage, deactivating it...", name)
            self.deactivatePluginByName(name, "bots")
            raise

    def deactivate_plugin_by_name(self, name):
        # TODO handle the "un"routing.

        pta_item = self.getPluginByName(name, 'bots')
        remove_plugin_templates_path(pta_item.path)
        try:
            return self.deactivatePluginByName(name, "bots")
        except Exception:
            add_plugin_templates_path(pta_item.path)
            raise

    def reload_plugin_by_name(self, name):
        """
        Completely reload the given plugin, including reloading of the module's code
        """
        was_activated = name in self.get_all_active_plugin_names()

        if was_activated:
            self.deactivate_plugin_by_name(name)

        plugin = self.get_plugin_by_name(name)

        module_alias = plugin.plugin_object.__module__
        module_old = __import__(module_alias)
        f = module_old.__file__
        if f.endswith('.pyc'):
            f = f[:-1]  # py2 compat : load the .py
        module_new = imp.load_source(module_alias, f)
        class_name = type(plugin.plugin_object).__name__
        new_class = getattr(module_new, class_name)
        plugin.plugin_object.__class__ = new_class

        if was_activated:
            self.activate_plugin(name)

    def update_plugin_places(self, path_list, extra_plugin_dir, autoinstall_deps=True):
        builtins = find_roots_with_extra(CORE_PLUGINS, extra_plugin_dir)

        paths = path_list
        if extra_plugin_dir:
            if isinstance(extra_plugin_dir, list):
                paths += extra_plugin_dir
            else:
                paths += [extra_plugin_dir, ]

        for entry in chain(builtins, paths):
            if entry not in sys.path:
                log.debug("Add %s to sys.path" % entry)
                sys.path.append(entry)  # so plugins can relatively import their repos

        dependencies_result = [check_dependencies(path) for path in paths]
        deps_to_install = set()
        if autoinstall_deps:
            for result in dependencies_result:
                if result:
                    deps_to_install.update(result[1])
            if deps_to_install:
                for dep in deps_to_install:
                    if dep.strip() != '':
                        log.info("Trying to install an unmet dependency: '%s'" % dep)
                        install_package(dep)
            errors = []
        else:
            errors = [result[0] for result in dependencies_result if result is not None]
        self.setPluginPlaces(chain(builtins, path_list))
        self.locatePlugins()

        self.all_candidates = [candidate[2] for candidate in self.getPluginCandidates()]

        # noinspection PyBroadException
        try:
            self.loadPlugins()
        except Exception:
            log.exception("Error while loading plugins")

        return errors

    def get_all_active_plugin_objects(self):
        return [plug.plugin_object
                for plug in self.getAllPlugins()
                if hasattr(plug, 'is_activated') and plug.is_activated]

    def get_all_active_plugin_names(self):
        return [p.name for p in self.getAllPlugins() if hasattr(p, 'is_activated') and p.is_activated]

    def get_all_plugin_names(self):
        return [p.name for p in self.getAllPlugins()]

    def deactivate_all_plugins(self):
        for name in self.get_all_active_plugin_names():
            self.deactivatePluginByName(name, "bots")

    # Repo management
    def get_installed_plugin_repos(self):

        repos = self.get(self.REPOS, {})

        if not repos:
            return repos

        # Fix to migrate exiting plugins into new format
        for url in self.get(self.REPOS, repos).values():
            if type(url) == dict:
                continue
            t_name = '/'.join(url.split('/')[-2:])
            name = t_name.replace('.git', '')

            t_repo = {name: {
                'path': url,
                'documentation': 'Unavilable',
                'python': None,
                'avatar_url': None,
                }
            }
            repos.update(t_repo)
        return repos

    def set_plugin_repos(self, repos):
        self[self.REPOS] = repos

    def add_plugin_repo(self, name, url):
        if PY2:
            name = name.encode('utf-8')
            url = url.encode('utf-8')
        repos = self.get_installed_plugin_repos()

        t_installed = {name: {
            'path': url,
            'documentation': 'Unavilable',
            'python': None,
            'avatar_url': None,
            }
        }

        repos.update(t_installed)
        self.set_plugin_repos(repos)

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
        return self.update_plugin_places(
            [self.plugin_dir + os.sep + d for d in self.get(self.REPOS, {}).keys()],
            self.extra, self.autoinstall_deps)

    def activate_non_started_plugins(self):
        log.info('Activating all the plugins...')
        configs = self[self.CONFIGS]
        errors = ''
        for pluginInfo in self.getAllPlugins():
            try:
                if self.is_plugin_blacklisted(pluginInfo.name):
                    errors += ('Notice: %s is blacklisted, use %s plugin unblacklist %s to unblacklist it\n') % (
                        self.prefix, pluginInfo.name, pluginInfo.name)
                    continue
                if hasattr(pluginInfo, 'is_activated') and not pluginInfo.is_activated:
                    log.info('Activate plugin: %s' % pluginInfo.name)
                    self.activate_plugin_with_version_check(pluginInfo.name, configs.get(pluginInfo.name, None))
            except Exception as e:
                log.exception("Error loading %s" % pluginInfo.name)
                errors += 'Error: %s failed to start : %s\n' % (pluginInfo.name, e)
        if errors:
            self.bot.warn_admins(errors)
        return errors

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
        return "Plugin %s activated." % name

    def deactivate_plugin(self, name):
        if name not in self.get_all_active_plugin_names():
            return "Plugin %s not in active list" % name
        self.deactivate_plugin_by_name(name)
        return "Plugin %s deactivated." % name

    def install_repo(self, repo):
        if repo in KNOWN_PUBLIC_REPOS:
            repo = KNOWN_PUBLIC_REPOS[repo]['path']  # replace it by the url
        git_path = which('git')

        if not git_path:
            return ('git command not found: You need to have git installed on '
                    'your system to be able to install git based plugins.', )

        # TODO: Update download path of plugin.
        if repo.endswith('tar.gz'):
            tar = TarFile(fileobj=urlopen(repo))
            tar.extractall(path=self.plugin_dir)
            s = repo.split(':')[-1].split('/')[-2:]
            human_name = '/'.join(s).rstrip('.tar.gz')
        else:
            human_name = human_name_for_git_url(repo)
            p = subprocess.Popen([git_path, 'clone', repo, human_name], cwd=self.plugin_dir, stdout=subprocess.PIPE,
                                 stderr=subprocess.PIPE)
            feedback = p.stdout.read().decode('utf-8')
            error_feedback = p.stderr.read().decode('utf-8')
            if p.wait():
                return "Could not load this plugin: \n\n%s\n\n---\n\n%s" % (feedback, error_feedback),
        self.add_plugin_repo(human_name, repo)
        return self.update_dynamic_plugins()

    def remove_plugin(self, plugin):
        """
        Deactivate and remove a plugin completely.
        :param plugin: the plugin to remove
        :return:
        """
        # First deactivate it if it was activated
        if hasattr(plugin, 'is_activated') and plugin.is_activated:
            self.deactivate_plugin(plugin.name)

        # Remove it from the candidate list (so it doesn't appear as a failed plugin)
        self.all_candidates.remove(plugin)

        # Remove it from yapsy itself
        for category, plugins in self.category_mapping.items():
            if plugin in plugins:
                log.debug('plugin found and removed from category %s', category)
                plugins.remove(plugin)

    def shutdown(self):
        log.info('Shutdown.')
        self.close_storage()
        log.info('Bye.')

    def __hash__(self):
        # Ensures this class (and subclasses) are hashable.
        # Presumably the use of mixins causes __hash__ to be
        # None otherwise.
        return int(id(self))
