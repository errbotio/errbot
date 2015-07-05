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

log = logging.getLogger(__name__)


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


def get_config(config_path):
    __import__('errbot.config-template')  # - is on purpose, it should not be imported normally ;)
    template = sys.modules['errbot.config-template']
    config_fullpath = config_path + sep + 'config.py'

    if not path.exists(config_fullpath):
        log.error(
            'I cannot find the file config.py in the directory %s \n'
            '(You can change this directory with the -c parameter see --help)' % config_path
        )
        log.info(
            'You can use the template %s as a base and copy it to %s. \nYou can then customize it.' % (
                path.dirname(template.__file__) + sep + 'config-template.py', config_path + sep)
        )
        exit(-1)

    # noinspection PyBroadException
    try:
        config = __import__('config')

        diffs = [item for item in set(dir(template)) - set(dir(config)) if not item.startswith('_')]
        if diffs:
            log.error('You are missing configs defined from the template :')
            for diff in diffs:
                log.error('Missing config : %s' % diff)
            exit(-1)
    except Exception as _:
        log.exception('I could not import your config from %s, please check the error below...' % config_fullpath)
        exit(-1)
    log.info('Config check passed...')
    return config


if __name__ == "__main__":

    execution_dir = getcwd()

    # By default insert the execution path (useful to be able to execute err from
    # the source tree directly without installing it.
    sys.path.insert(0, execution_dir)

    parser = argparse.ArgumentParser(description='The main entry point of the XMPP bot err.')
    parser.add_argument('-c', '--config', default=None,
                        help='Specify the directory where your config.py is (default: current working directory).')
    parser.add_argument('-r', '--restore', nargs='?', default=None, const='default',
                        help='Restores a bot from backup.py. (default: backup.py from the bot data directory).')
    parser.add_argument('-l', '--list', action='store_true', help='Lists all the backends found.')

    backend_group = parser.add_mutually_exclusive_group()
    backend_group.add_argument('-X', '--xmpp', action='store_true', help='XMPP backend [DEFAULT]')
    backend_group.add_argument('-H', '--hipchat', action='store_true', help='Hipchat backend')
    backend_group.add_argument('-C', '--campfire', action='store_true', help='campfire backend')
    backend_group.add_argument('-I', '--irc', action='store_true', help='IRC backend')
    backend_group.add_argument('-O', '--tox', action='store_true', help='TOX backend')
    backend_group.add_argument('-S', '--slack', action='store_true', help='Slack backend')
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

    config = get_config(config_path)  # will exit if load fails
    if args['list']:
        from errbot.main import enumerate_backends
        print('Available backends:')
        for backend_name in enumerate_backends(config):
            print('\t\t%s' % backend_name)
        sys.exit(0)

    # this is temporary until the modes are removed to translate the mode names to backend names
    classic_vs_plugin_names = {'text': 'Text',
                               'graphic': 'Graphic',
                               'campfire': 'Campfire',
                               'hipchat': 'Hipchat',
                               'irc': 'IRC',
                               'xmpp': 'XMPP',
                               'tox': 'TOX',
                               'slack': 'Slack',
                               'null': 'Null'}

    filtered_mode = [mname for mname in classic_vs_plugin_names.keys() if args[mname]]
    if args['restore']:
        backend = 'Null'  # we don't want any backend when we restore
    elif filtered_mode:
        backend = classic_vs_plugin_names[filtered_mode[0]]
        if backend != 'Text':
            log.warn("""Deprecation notice:
            Please add BACKEND='%s' to your config.py instead of using the '--%s' command line parameter.
            The backend command line parameters will be removed on the next version of Err.
            """ % (backend, filtered_mode[0]))
    elif hasattr(config, 'BACKEND'):
        backend = config.BACKEND
    else:
        log.warn("""Deprecation notice:
        Err is defaulting to XMPP because you did not specify any backend.
        Please add BACKEND='XMPP' to your config.py if you really want that.
        This behaviour will be removed on the next version of Err.
        """)
        backend = 'XMPP'  # default value

    log.info("Selected backend '%s'." % backend)

    # Check if at least we can start to log something before trying to start
    # the bot (esp. daemonize it).

    log.info("Checking for '%s'..." % config.BOT_DATA_DIR)
    if not path.exists(config.BOT_DATA_DIR):
        raise Exception("The data directory '%s' for the bot does not exist" % config.BOT_DATA_DIR)
    if not access(config.BOT_DATA_DIR, W_OK):
        raise Exception("The data directory '%s' should be writable for the bot" % config.BOT_DATA_DIR)

    if (not ON_WINDOWS) and args['daemon']:
        if args['text']:
            raise Exception('You cannot run in text and daemon mode at the same time')
        if args['restore']:
            raise Exception('You cannot restore a backup in daemon mode.')
        if args['pidfile']:
            pid = args['pidfile']
        else:
            pid = config.BOT_DATA_DIR + sep + 'err.pid'

        from errbot.pid import PidFile

        pidfile = PidFile(pid)

        # noinspection PyBroadException
        try:
            def action():
                from errbot.main import main
                main(backend_name, logger, config)

            daemon = Daemonize(app="err", pid=pid, action=action)
            daemon.start()
        except Exception:
            log.exception('Failed to daemonize the process')
        exit(0)
    from errbot.main import main
    restore = args['restore']
    if restore == 'default':  # restore with no argument, get the default location
        restore = path.join(config.BOT_DATA_DIR, 'backup.py')

    main(backend, logger, config, restore)
    log.info('Process exiting')
