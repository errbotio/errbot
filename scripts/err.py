#!/usr/bin/python2.7

#    This program is free software; you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation; either version 3 of the License, or
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
import os
import sys
import argparse

def main():
    # from here the environment is supposed to be set (daemon / non daemon,
    # config.py in the python path )
    from errbot.utils import PLUGINS_SUBDIR
    from errbot.errBot import ErrBot
    from errbot import holder
    from config import BOT_IDENTITY, BOT_LOG_LEVEL, BOT_DATA_DIR, BOT_LOG_FILE

    holder.bot = ErrBot(**BOT_IDENTITY)
    logging.basicConfig(format='%(levelname)s:%(message)s')
    logger = logging.getLogger('')
    if BOT_LOG_FILE:
        hdlr = logging.FileHandler(BOT_LOG_FILE)
        hdlr.setFormatter(logging.Formatter('%(asctime)s %(levelname)s %(message)s'))
        logger.addHandler(hdlr)
    logger.setLevel(BOT_LOG_LEVEL)

    d = os.path.dirname(BOT_DATA_DIR)
    if not os.path.exists(d):
        raise Exception('The data directory %s for the bot does not exist' % BOT_DATA_DIR)
    if not os.access(BOT_DATA_DIR, os.W_OK):
        raise Exception('The data directory %s should be writable for the bot' % BOT_DATA_DIR)

    # make the plugins subdir to store the plugin shelves
    d = BOT_DATA_DIR + os.sep + PLUGINS_SUBDIR
    if not os.path.exists(d):
        os.makedirs(d)

    holder.bot.update_dynamic_plugins()
    logging.debug('serve from %s' % holder.bot)
    holder.bot.serve_forever()

# Default daemon parameters.
# File mode creation mask of the daemon.
UMASK = 0

# Default maximum for the number of available file descriptors.
MAXFD = 1024
WORKDIR = '/'

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='The main entry point of the XMPP bot err.')
    parser.add_argument('-d', '--daemon', action='store_true', help='Detach the process from the console')
    parser.add_argument('-c', '--config', default=os.getcwd(), help='Specify the directory where your config.py is (default: current working directory)')
    args = vars(parser.parse_args()) # create a dictionary of args

    # setup the enrvironment to be able to import the config.py
    sys.path.append(args['config']) # appends the current directory in order to find config.py
    if args['daemon']:
        try:
            pid = os.fork()
        except OSError, e:
            raise Exception, "%s [%d]" % (e.strerror, e.errno)
        if not pid: # first child
            os.setsid()
            try:
                pid = os.fork()
            except OSError, e:
                raise Exception, "%s [%d]" % (e.strerror, e.errno)
            if not pid: # second child (zombie prevention)
                os.chdir(WORKDIR)
                os.umask(UMASK)
            else:
                os._exit(0)
        else:
            os._exit(0)
        import resource

        maxfd = resource.getrlimit(resource.RLIMIT_NOFILE)[1]
        if maxfd == resource.RLIM_INFINITY:
            maxfd = MAXFD
        for fd in range(0, maxfd):
            try:
                os.close(fd)
            except OSError:   # ERROR, fd wasn't open to begin with (ignored)
                pass
        os.open(os.devnull, os.O_RDWR)
        os.dup2(0, 1)
        os.dup2(0, 2)
    main()
