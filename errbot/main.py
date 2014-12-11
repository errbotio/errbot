from os import path, makedirs, sep
import logging


def main(bot_class, logger, config):
    # from here the environment is supposed to be set (daemon / non daemon,
    # config.py in the python path )

    from errbot.utils import PLUGINS_SUBDIR
    from errbot import holder
    from errbot.errBot import main_config_defaults
    main_config_defaults(config)

    if config.BOT_LOG_FILE:
        hdlr = logging.FileHandler(config.BOT_LOG_FILE)
        hdlr.setFormatter(logging.Formatter('%(asctime)s %(levelname)s %(message)s'))
        logger.addHandler(hdlr)

    if config.BOT_LOG_SENTRY:
        try:
            from raven.handlers.logging import SentryHandler
        except ImportError as _:
            logging.exception(
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
        logging.exception("Unable to configure the backend, please check if your config.py is correct.")
        exit(-1)
    errors = holder.bot.update_dynamic_plugins()
    if errors:
        logging.error('Some plugins failed to load:\n' + '\n'.join(errors))
    logging.debug('serve from %s' % holder.bot)
    holder.bot.serve_forever()
