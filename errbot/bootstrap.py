from os import path, makedirs
import importlib
import logging
import sys

from errbot.core import ErrBot
from errbot.plugin_manager import BotPluginManager
from errbot.repo_manager import BotRepoManager
from errbot.backend_plugin_manager import BackendPluginManager
from errbot.storage.base import StoragePluginBase
from errbot.utils import PLUGINS_SUBDIR
from errbot.logs import format_logs

log = logging.getLogger(__name__)

HERE = path.dirname(path.abspath(__file__))
CORE_BACKENDS = path.join(HERE, 'backends')
CORE_STORAGE = path.join(HERE, 'storage')

PLUGIN_DEFAULT_INDEX = 'https://repos.errbot.io/repos.json'


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
    if not hasattr(config, 'BOT_PREFIX'):
        config.BOT_PREFIX = '!'
    if not hasattr(config, 'BOT_ALT_PREFIXES'):
        config.BOT_ALT_PREFIXES = ()
    if not hasattr(config, 'BOT_ALT_PREFIX_SEPARATORS'):
        config.BOT_ALT_PREFIX_SEPARATORS = ()
    if not hasattr(config, 'BOT_ALT_PREFIX_CASEINSENSITIVE'):
        config.BOT_ALT_PREFIX_CASEINSENSITIVE = False
    if not hasattr(config, 'DIVERT_TO_PRIVATE'):
        config.DIVERT_TO_PRIVATE = ()
    if not hasattr(config, 'DIVERT_TO_THREAD'):
        config.DIVERT_TO_THREAD = ()
    if not hasattr(config, 'MESSAGE_SIZE_LIMIT'):
        config.MESSAGE_SIZE_LIMIT = 10000  # Corresponds with what HipChat accepts
    if not hasattr(config, 'GROUPCHAT_NICK_PREFIXED'):
        config.GROUPCHAT_NICK_PREFIXED = False
    if not hasattr(config, 'AUTOINSTALL_DEPS'):
        config.AUTOINSTALL_DEPS = True
    if not hasattr(config, 'SUPPRESS_CMD_NOT_FOUND'):
        config.SUPPRESS_CMD_NOT_FOUND = False
    if not hasattr(config, 'BOT_ASYNC'):
        config.BOT_ASYNC = True
    if not hasattr(config, 'BOT_ASYNC_POOLSIZE'):
        config.BOT_ASYNC_POOLSIZE = 10
    if not hasattr(config, 'CHATROOM_PRESENCE'):
        config.CHATROOM_PRESENCE = ()
    if not hasattr(config, 'CHATROOM_RELAY'):
        config.CHATROOM_RELAY = ()
    if not hasattr(config, 'REVERSE_CHATROOM_RELAY'):
        config.REVERSE_CHATROOM_RELAY = ()
    if not hasattr(config, 'CHATROOM_FN'):
        config.CHATROOM_FN = 'Errbot'
    if not hasattr(config, 'TEXT_DEMO_MODE'):
        config.TEXT_DEMO_MODE = True
    if not hasattr(config, 'BOT_ADMINS'):
        raise ValueError('BOT_ADMINS missing from config.py.')
    if not hasattr(config, 'TEXT_COLOR_THEME'):
        config.TEXT_COLOR_THEME = 'light'
    if not hasattr(config, 'BOT_ADMINS_NOTIFICATIONS'):
        config.BOT_ADMINS_NOTIFICATIONS = config.BOT_ADMINS


def setup_bot(backend_name: str, logger, config, restore=None) -> ErrBot:
    # from here the environment is supposed to be set (daemon / non daemon,
    # config.py in the python path )

    bot_config_defaults(config)

    if hasattr(config, 'BOT_LOG_FORMATTER'):
        format_logs(formatter=config.BOT_LOG_FORMATTER)
    else:
        format_logs(theme_color=config.TEXT_COLOR_THEME)

        if config.BOT_LOG_FILE:
            hdlr = logging.FileHandler(config.BOT_LOG_FILE)
            hdlr.setFormatter(logging.Formatter("%(asctime)s %(levelname)-8s %(name)-25s %(message)s"))
            logger.addHandler(hdlr)

    if hasattr(config, 'BOT_LOG_SENTRY') and config.BOT_LOG_SENTRY:
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

        try:
            if hasattr(config, 'SENTRY_TRANSPORT') and isinstance(config.SENTRY_TRANSPORT, tuple):
                mod = importlib.import_module(config.SENTRY_TRANSPORT[1])
                transport = getattr(mod, config.SENTRY_TRANSPORT[0])

                sentryhandler = SentryHandler(config.SENTRY_DSN,
                                              level=config.SENTRY_LOGLEVEL,
                                              transport=transport)
            else:
                sentryhandler = SentryHandler(config.SENTRY_DSN, level=config.SENTRY_LOGLEVEL)
            logger.addHandler(sentryhandler)
        except ImportError:
            log.exception(f'Unable to import selected SENTRY_TRANSPORT - {config.SENTRY_TRANSPORT}')
            exit(-1)

    logger.setLevel(config.BOT_LOG_LEVEL)

    storage_plugin = get_storage_plugin(config)

    # init the botplugin manager
    botplugins_dir = path.join(config.BOT_DATA_DIR, PLUGINS_SUBDIR)
    if not path.exists(botplugins_dir):
        makedirs(botplugins_dir, mode=0o755)

    plugin_indexes = getattr(config, 'BOT_PLUGIN_INDEXES', (PLUGIN_DEFAULT_INDEX,))
    if isinstance(plugin_indexes, str):
        plugin_indexes = (plugin_indexes, )

    backendpm = BackendPluginManager(config, 'errbot.backends', backend_name,
                                     ErrBot, CORE_BACKENDS, getattr(config, 'BOT_EXTRA_BACKEND_DIR', []))

    log.info(f'Found Backend plugin: {backendpm.plugin_info.name}')

    repo_manager = BotRepoManager(storage_plugin,
                                  botplugins_dir,
                                  plugin_indexes)

    try:
        bot = backendpm.load_plugin()
        botpm = BotPluginManager(storage_plugin,
                                 config.BOT_EXTRA_PLUGIN_DIR,
                                 config.AUTOINSTALL_DEPS,
                                 getattr(config, 'CORE_PLUGINS', None),
                                 lambda name, clazz: clazz(bot, name),
                                 getattr(config, 'PLUGINS_CALLBACK_ORDER', (None, )))
        bot.attach_storage_plugin(storage_plugin)
        bot.attach_repo_manager(repo_manager)
        bot.attach_plugin_manager(botpm)
        bot.initialize_backend_storage()

        # restore the bot from the restore script
        if restore:
            # Prepare the context for the restore script
            if 'repos' in bot:
                log.fatal('You cannot restore onto a non empty bot.')
                sys.exit(-1)
            log.info(f'**** RESTORING the bot from {restore}')
            restore_bot_from_backup(restore, bot=bot, log=log)
            print('Restore complete. You can restart the bot normally')
            sys.exit(0)

        errors = bot.plugin_manager.update_plugin_places(repo_manager.get_all_repos_paths())
        if errors:
            log.error('Some plugins failed to load:\n' + '\n'.join(errors.values()))
            bot._plugin_errors_during_startup = "\n".join(errors.values())
        return bot
    except Exception:
        log.exception("Unable to load or configure the backend.")
        exit(-1)


def restore_bot_from_backup(backup_filename, *, bot, log):
    """Restores the given bot by executing the 'backup' script.

    The backup file is a python script which manually execute a series of commands on the bot to restore it
    to its previous state.

    :param backup_filename: the full path to the backup script.
    :param bot: the bot instance to restore
    :param log: logger to use during the restoration process
    """
    with open(backup_filename) as f:
        exec(f.read(), {'log': log, 'bot': bot})
    bot.close_storage()


def get_storage_plugin(config):
    """
    Find and load the storage plugin
    :param config: the bot configuration.
    :return: the storage plugin
    """
    storage_name = getattr(config, 'STORAGE', 'Shelf')
    extra_storage_plugins_dir = getattr(config, 'BOT_EXTRA_STORAGE_PLUGINS_DIR', None)
    spm = BackendPluginManager(config, 'errbot.storage', storage_name, StoragePluginBase,
                               CORE_STORAGE, extra_storage_plugins_dir)
    log.info(f'Found Storage plugin: {spm.plugin_info.name}.')
    return spm.load_plugin()


def bootstrap(bot_class, logger, config, restore=None):
    """
    Main starting point of Errbot.

    :param bot_class: The backend class inheriting from Errbot you want to start.
    :param logger: The logger you want to use.
    :param config: The config.py module.
    :param restore: Start Errbot in restore mode (from a backup).
    """
    bot = setup_bot(bot_class, logger, config, restore)
    log.debug(f'Start serving commands from the {bot.mode} backend.')
    bot.serve_forever()
