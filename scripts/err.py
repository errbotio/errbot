#!/usr/bin/env python

# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 3 of the License, or
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

import logging
from colorlog import ColoredFormatter
import sys
import argparse
from os import path, sep, getcwd, access, W_OK
from platform import system
import inspect


# noinspection PyUnusedLocal
def debug(sig, frame):
    """Interrupt running process, and provide a python prompt for
    interactive debugging."""
    d = {'_frame': frame}  # Allow access to frame object.
    d.update(frame.f_globals)  # Unless shadowed by global
    d.update(frame.f_locals)

    i = code.InteractiveConsole(d)
    message = "Signal received : entering python shell.\nTraceback:\n"
    message += ''.join(traceback.format_stack(frame))
    i.interact(message)


def ispydevd():
    for frame in inspect.stack():
        if frame[1].endswith("pydevd.py"):
            return True
    return False

ON_WINDOWS = system() == 'Windows'

if not ON_WINDOWS:
    from daemonize import Daemonize
    from pwd import getpwnam
    from grp import getgrnam
    import code
    import traceback
    import signal

    signal.signal(signal.SIGUSR1, debug)  # Register handler for debugging

logger = logging.getLogger('')
logging.getLogger('yapsy').setLevel(logging.INFO)  # this one is way too verbose in debug
logging.getLogger('Rocket.Errors.ThreadPool').setLevel(logging.INFO)  # this one is way too verbose in debug
logger.setLevel(logging.INFO)

pydev = ispydevd()
stream = sys.stdout if pydev else sys.stderr
isatty = pydev or stream.isatty()  # force isatty if we are under pydev because it supports coloring anyway.
console_hdlr = logging.StreamHandler(stream)

if isatty:
    formatter = ColoredFormatter(
        "%(asctime)s %(log_color)s%(levelname)-8s%(reset)s "
        "%(blue)s%(name)-25.25s%(reset)s %(white)s%(message)s%(reset)s",
        datefmt="%H:%M:%S",
        reset=True,
        log_colors={
            'DEBUG': 'cyan',
            'INFO': 'green',
            'WARNING': 'yellow',
            'ERROR': 'red',
            'CRITICAL': 'red',
        }
    )
    console_hdlr.setFormatter(formatter)
else:
    console_hdlr.setFormatter(logging.Formatter("%(levelname)-8s %(name)-25s %(message)s"))
logger.addHandler(console_hdlr)


def check_config(config_path, mode):
    __import__('errbot.config-template')  # - is on purpose, it should not be imported normally ;)
    template = sys.modules['errbot.config-template']
    config_fullpath = config_path + sep + 'config.py'

    if not path.exists(config_fullpath):
        logging.error(
            'I cannot find the file config.py in the directory %s \n'
            '(You can change this directory with the -c parameter see --help)' % config_path
        )
        logging.info(
            'You can use the template %s as a base and copy it to %s. \nYou can then customize it.' % (
                path.dirname(template.__file__) + sep + 'config-template.py', config_path + sep)
        )
        exit(-1)

    # noinspection PyBroadException
    try:
        try:
            # gives the opportunity to have one config per mode to simplify the debugging
            config = __import__('config_' + mode)
            sys.modules['config'] = config
        except ImportError as ie:
            if not str(ie).startswith('No module named'):
                logging.exception('Error while trying to load %s' % 'config_' + mode)
            import config

        diffs = [item for item in set(dir(template)) - set(dir(config)) if not item.startswith('_')]
        if diffs:
            logging.error('You are missing configs defined from the template :')
            for diff in diffs:
                logging.error('Missing config : %s' % diff)
            exit(-1)
    except Exception as _:
        logging.exception('I could not import your config from %s, please check the error below...' % config_fullpath)
        exit(-1)
    logging.info('Config check passed...')


if __name__ == "__main__":

    execution_dir = getcwd()

    # By default insert the execution path (useful to be able to execute err from
    # the source tree directly without installing it.
    sys.path.insert(0, execution_dir)

    parser = argparse.ArgumentParser(description='The main entry point of the XMPP bot err.')
    parser.add_argument('-c', '--config', default=None,
                        help='Specify the directory where your config.py is (default: current working directory)')
    backend_group = parser.add_mutually_exclusive_group()
    backend_group.add_argument('-X', '--xmpp', action='store_true', help='XMPP backend [DEFAULT]')
    backend_group.add_argument('-H', '--hipchat', action='store_true', help='Hipchat backend')
    backend_group.add_argument('-C', '--campfire', action='store_true', help='campfire backend')
    backend_group.add_argument('-I', '--irc', action='store_true', help='IRC backend')
    backend_group.add_argument('-O', '--tox', action='store_true', help='TOX backend')
    backend_group.add_argument('-T', '--text', action='store_true', help='locale text debug backend')
    backend_group.add_argument('-G', '--graphic', action='store_true', help='local graphical debug mode backend')
    backend_group.add_argument('-N', '--null', action='store_true', help='no backend')

    if not ON_WINDOWS:
        option_group = parser.add_argument_group('arguments to run it as a Daemon')
        option_group.add_argument('-d', '--daemon', action='store_true', help='Detach the process from the console')
        option_group.add_argument('-p', '--pidfile', default=None,
                                  help='Specify the pid file for the daemon (default: current bot data directory)')

    args = vars(parser.parse_args())  # create a dictionary of args
    config_path = args['config']
    # setup the environment to be able to import the config.py
    if config_path:
        sys.path.insert(0, config_path)  # appends the current config in order to find config.py
    else:
        config_path = execution_dir
    filtered_mode = [mname for mname in ('text', 'graphic', 'campfire', 'hipchat', 'irc', 'xmpp', 'tox', 'null') if
                     args[mname]]
    mode = filtered_mode[0] if filtered_mode else 'xmpp'  # default value

    check_config(config_path, mode)  # check if everything is ok before attempting to start

    def text():
        from errbot.backends.text import TextBackend

        return TextBackend

    def graphic():
        from errbot.backends.graphic import GraphicBackend

        return GraphicBackend

    def campfire():
        from errbot.backends.campfire import CampfireBackend

        return CampfireBackend

    def hipchat():
        from errbot.backends.hipchat import HipchatBackend

        return HipchatBackend

    def irc():
        from errbot.backends.irc import IRCBackend

        return IRCBackend

    def xmpp():
        from errbot.backends.xmpp import XMPPBackend

        return XMPPBackend

    def tox():
        from errbot.backends.tox import ToxBackend

        return ToxBackend

    def null():
        from errbot.backends.null import NullBackend

        return NullBackend

    bot_class = locals()[mode]()
    # Check if at least we can start to log something before trying to start
    # the bot (esp. daemonize it).
    from config import BOT_DATA_DIR

    logging.info("Checking for '%s'..." % BOT_DATA_DIR)
    if not path.exists(BOT_DATA_DIR):
        raise Exception("The data directory '%s' for the bot does not exist" % BOT_DATA_DIR)
    if not access(BOT_DATA_DIR, W_OK):
        raise Exception("The data directory '%s' should be writable for the bot" % BOT_DATA_DIR)

    if (not ON_WINDOWS) and args['daemon']:
        if args['text']:
            raise Exception('You cannot run in text and daemon mode at the same time')

        if args['pidfile']:
            pid = args['pidfile']
        else:
            pid = BOT_DATA_DIR + sep + 'err.pid'

        from errbot.pid import PidFile

        pidfile = PidFile(pid)

        # noinspection PyBroadException
        try:
            def action():
                from errbot.main import main

                main(bot_class, logger)

            daemon = Daemonize(app="err", pid=pid, action=action)
            daemon.start()
        except Exception:
            logging.exception('Failed to daemonize the process')
        exit(0)
    from errbot.main import main

    main(bot_class, logger)
    logging.info('Process exiting')
