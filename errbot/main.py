from os import path, makedirs
import logging

from errbot.errBot import ErrBot
from errbot.plugin_manager import BotPluginManager
from errbot.repo_manager import BotRepoManager
from errbot.specific_plugin_manager import SpecificPluginManager
import sys

from errbot.storage.base import StoragePluginBase
from errbot.utils import PLUGINS_SUBDIR, is_str

log = logging.getLogger(__name__)

HERE = path.dirname(path.abspath(__file__))
CORE_BACKENDS = path.join(HERE, 'backends')
CORE_STORAGE = path.join(HERE, 'storage')

PLUGIN_DEFAULT_INDEX = 'https://repos.errbot.io/repos.json'


def setup_bot(backend_name, logger, config, restore=None):
    # from here the environment is supposed to be set (daemon / non daemon,
    # config.py in the python path )

    from .errBot import bot_config_defaults

    bot_config_defaults(config)

    if config.BOT_LOG_FILE:
        hdlr = logging.FileHandler(config.BOT_LOG_FILE)
        hdlr.setFormatter(logging.Formatter("%(asctime)s %(levelname)-8s %(name)-25s %(message)s"))
        logger.addHandler(hdlr)

    if config.BOT_LOG_SENTRY:
        try:
            from raven.handlers.logging import SentryHandler
        except ImportError:
            log.exception(
                "You have BOT_LOG_SENTRY enabled, but I couldn't import modules "
                "needed for Sentry integration. Did you install raven? "
                "(See http://raven.readthedocs.org/en/latest/install/index.html "
                "for installation instructions)"
            )
            exit(-1)

        sentryhandler = SentryHandler(config.SENTRY_DSN, level=config.SENTRY_LOGLEVEL)
        logger.addHandler(sentryhandler)

    logger.setLevel(config.BOT_LOG_LEVEL)

    storage_plugin = get_storage_plugin(config)

    # init the botplugin manager
    botplugins_dir = path.join(config.BOT_DATA_DIR, PLUGINS_SUBDIR)
    if not path.exists(botplugins_dir):
        makedirs(botplugins_dir, mode=0o755)

    plugin_indexes = getattr(config, 'BOT_PLUGIN_INDEXES', (PLUGIN_DEFAULT_INDEX,))
    if is_str(plugin_indexes):
        plugin_indexes = (plugin_indexes, )

    repo_manager = BotRepoManager(storage_plugin,
                                  botplugins_dir,
                                  plugin_indexes)
    botpm = BotPluginManager(storage_plugin,
                             repo_manager,
                             config.BOT_EXTRA_PLUGIN_DIR,
                             config.AUTOINSTALL_DEPS,
                             getattr(config, 'CORE_PLUGINS', None))

    # init the backend manager & the bot
    backendpm = bpm_from_config(config)

    backend_plug = backendpm.get_candidate(backend_name)

    log.info("Found Backend plugin: '%s'\n\t\t\t\t\t\tDescription: %s" % (backend_plug.name, backend_plug.description))

    try:
        bot = backendpm.get_plugin_by_name(backend_name)
        bot.attach_storage_plugin(storage_plugin)
        bot.attach_repo_manager(repo_manager)
        bot.attach_plugin_manager(botpm)
        bot.initialize_backend_storage()
    except Exception:
        log.exception("Unable to load or configure the backend.")
        exit(-1)

    # restore the bot from the restore script
    if restore:
        # Prepare the context for the restore script
        if 'repos' in bot:
            log.fatal('You cannot restore onto a non empty bot.')
            sys.exit(-1)
        log.info('**** RESTORING the bot from %s' % restore)
        with open(restore) as f:
            exec(f.read())
        bot.close_storage()
        print('Restore complete. You can restart the bot normally')
        sys.exit(0)

    errors = bot.plugin_manager.update_dynamic_plugins()
    if errors:
        log.error('Some plugins failed to load:\n' + '\n'.join(errors.values()))
        bot._plugin_errors_during_startup = "\n".join(errors.values())
    return bot


def get_storage_plugin(config):
    """
    Find and load the storage plugin
    :param config: the bot configuration.
    :return: the storage plugin
    """
    storage_name = getattr(config, 'STORAGE', 'Shelf')
    extra_storage_plugins_dir = getattr(config, 'BOT_EXTRA_STORAGE_PLUGINS_DIR', None)
    spm = SpecificPluginManager(config, 'storage', StoragePluginBase, CORE_STORAGE, extra_storage_plugins_dir)
    storage_pluginfo = spm.get_candidate(storage_name)
    log.info("Found Storage plugin: '%s'\nDescription: %s" % (storage_pluginfo.name, storage_pluginfo.description))
    storage_plugin = spm.get_plugin_by_name(storage_name)
    return storage_plugin


def bpm_from_config(config):
    """Creates a backend plugin manager from a given config."""
    extra = getattr(config, 'BOT_EXTRA_BACKEND_DIR', [])
    return SpecificPluginManager(
            config,
            'backends',
            ErrBot,
            CORE_BACKENDS,
            extra_search_dirs=extra)


def enumerate_backends(config):
    """ Returns all the backends found for the given config.
    """
    bpm = bpm_from_config(config)
    return [plug.name for (_, _, plug) in bpm.getPluginCandidates()]


def main(bot_class, logger, config, restore=None):
    bot = setup_bot(bot_class, logger, config, restore)
    log.debug('Start serving commands from the %s backend' % bot.mode)
    bot.serve_forever()
