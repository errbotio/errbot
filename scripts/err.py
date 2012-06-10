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
import daemon

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

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='The main entry point of the XMPP bot err.')
    parser.add_argument('-d', '--daemon', action='store_true', help='Detach the process from the console')
    parser.add_argument('-c', '--config', default=os.getcwd(), help='Specify the directory where your config.py is (default: current working directory)')
    args = vars(parser.parse_args()) # create a dictionary of args

    # setup the environment to be able to import the config.py
    sys.path.append(args['config']) # appends the current directory in order to find config.py
    if args['daemon']:
        with daemon.DaemonContext(detach_process=True,working_directory=os.getcwd()): # put the initial working directory to be sure not to lost it after daemonization
            main()
    else:
        main()
    logging.info('Process exiting')
