from os import path, makedirs
import logging
from errbot.backend_manager import BackendManager
import sys

log = logging.getLogger(__name__)


def setup_bot(backend_name, logger, config, restore=None):
    # from here the environment is supposed to be set (daemon / non daemon,
    # config.py in the python path )

    from .utils import PLUGINS_SUBDIR
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

    # make the plugins subdir to store the plugin shelves
    d = path.join(config.BOT_DATA_DIR, PLUGINS_SUBDIR)
    if not path.exists(d):
        makedirs(d, mode=0o755)

    # instanciate the bot
    bpm = BackendManager(config)

    plug = bpm.get_candidate(backend_name)

    log.info("Found Backend plugin: '%s'\n\t\t\t\t\t\tDescription: %s" % (plug.name, plug.description))

    try:
        bot = bpm.get_backend_by_name(backend_name)
    except Exception:
        log.exception("Unable to configure the backend, please check if your config.py is correct.")
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

    errors = bot.update_dynamic_plugins()
    if errors:
        log.error('Some plugins failed to load:\n' + '\n'.join(errors))
    return bot


def enumerate_backends(config):
    """ Returns all the backends found for the given config.
    """
    bpm = BackendManager(config)
    return [plug.name for (_, _, plug) in bpm.getPluginCandidates()]


def main(bot_class, logger, config, restore=None):
    bot = setup_bot(bot_class, logger, config, restore)
    log.debug('serve from %s' % bot)
    bot.serve_forever()
