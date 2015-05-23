from os import path, makedirs, sep
import logging

log = logging.getLogger(__name__)


def main(bot_class, logger, config):
    # from here the environment is supposed to be set (daemon / non daemon,
    # config.py in the python path )

    from .utils import PLUGINS_SUBDIR
    from . import holder
    from .errBot import bot_config_defaults
    bot_config_defaults(config)

    if config.BOT_LOG_FILE:
        hdlr = logging.FileHandler(config.BOT_LOG_FILE)
        hdlr.setFormatter(logging.Formatter('%(asctime)s %(levelname)s %(message)s'))
        logger.addHandler(hdlr)

    if config.BOT_LOG_SENTRY:
        try:
            from raven.handlers.logging import SentryHandler
        except ImportError as _:
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
    try:
        holder.bot = bot_class(config)
    except Exception:
        log.exception("Unable to configure the backend, please check if your config.py is correct.")
        exit(-1)
    errors = holder.bot.update_dynamic_plugins()
    if errors:
        log.error('Some plugins failed to load:\n' + '\n'.join(errors))
    log.debug('serve from %s' % holder.bot)
    holder.bot.serve_forever()
