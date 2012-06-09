#!/usr/bin/python
# -*- coding: utf-8 -*-

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
from datetime import datetime
import inspect

import logging
import os
import shelve
import shutil
import subprocess
from tarfile import TarFile
from urllib2 import urlopen
from config import BOT_DATA_DIR, BOT_ADMINS, BOT_LOG_FILE

from errbot.jabberbot import JabberBot, botcmd
from errbot.plugin_manager import get_all_active_plugin_names, activate_plugin, deactivate_plugin, activate_all_plugins, deactivate_all_plugins, update_plugin_places, get_all_active_plugin_objects, get_all_plugins
from errbot.utils import get_jid_from_message, PLUGINS_SUBDIR, human_name_for_git_url, tail, format_timedelta
from errbot.repos import KNOWN_PUBLIC_REPOS

PLUGIN_DIR = BOT_DATA_DIR + os.sep + PLUGINS_SUBDIR

def get_class_that_defined_method(meth):
  obj = meth.im_self
  for cls in inspect.getmro(meth.im_class):
    if meth.__name__ in cls.__dict__: return cls
  return None

def admin_only(mess):
    if mess.getType() == 'groupchat':
        raise Exception('You cannot administer the bot from a chatroom, message the bot directly')
    usr = get_jid_from_message(mess)
    if usr not in BOT_ADMINS:
        raise Exception('You cannot administer the bot from this user %s.' % usr)

class ErrBot(JabberBot):
    """ Commands related to the bot administration """
    MSG_ERROR_OCCURRED = 'Computer says nooo. See logs for details.'
    MSG_UNKNOWN_COMMAND = 'Unknown command: "%(command)s". '
    internal_shelf = shelve.DbfilenameShelf(BOT_DATA_DIR + os.sep + 'core.db')

    # Repo management
    def get_installed_plugin_repos(self):
        return self.internal_shelf.get('repos', {})

    def add_plugin_repo(self, name, url):
        repos = self.get_installed_plugin_repos()
        repos[name] = url
        self.internal_shelf['repos'] = repos
        self.internal_shelf.sync()


    # this will load the plugins the admin has setup at runtime
    def update_dynamic_plugins(self):
        update_plugin_places([PLUGIN_DIR + os.sep + d for d in self.internal_shelf.get('repos', {}).keys()])

    def __init__(self, username, password, res=None, debug=False,
                 privatedomain=False, acceptownmsgs=False, handlers=None):
        JabberBot.__init__(self, username, password, res, debug, privatedomain, acceptownmsgs, handlers)

    def callback_message(self, conn, mess):
        super(ErrBot, self).callback_message(conn, mess)
        for bot in get_all_active_plugin_objects():
            if hasattr(bot, 'callback_message'):
                try:
                    bot.callback_message(conn, mess)
                except:
                    logging.exception("Probably a type error")

    def activate_non_started_plugins(self):
        logging.info('Activating all the plugins...')
        activate_all_plugins()

    def signal_connect_to_all_plugins(self):
        for bot in get_all_active_plugin_objects():
            if hasattr(bot, 'callback_connect'):
                try:
                    bot.callback_connect()
                except:
                    logging.exception("callback_connect failed for %s" % bot)

    def connect(self):
        if not self.conn:
            self.conn = JabberBot.connect(self)
            self.activate_non_started_plugins()
            logging.info('Notifying connection to all the plugins...')
            self.signal_connect_to_all_plugins()
            logging.info('Plugin activation done.')
        return self.conn

    def shutdown(self):
        logging.info('Shutting down... deactivating all the plugins.')
        deactivate_all_plugins()
        self.internal_shelf.close()
        logging.info('Bye.')

    @botcmd
    def status(self, mess, args):
        """ If I am alive I should be able to respond to this one
        """
        return 'I am alive with those plugins :\n' + '\n'.join(get_all_active_plugin_names())

    startup_time = datetime.now()

    @botcmd
    def uptime(self, mess, args):
        """ Return the uptime of the bot
        """
        return 'I up for %s %s (since %s)' % (args, format_timedelta(datetime.now() - self.startup_time), datetime.strftime(self.startup_time, '%A, %b %d at %H:%M'))

    @botcmd
    def restart(self, mess, args):
        """ restart the bot """
        admin_only(mess)
        self.quit(-1337)
        return "I'm restarting..."

    @botcmd
    def load(self, mess, args):
        """load a plugin"""
        admin_only(mess)
        result = activate_plugin(args)
        #self.refresh_command_list()
        return result

    @botcmd
    def unload(self, mess, args):
        """unload a plugin"""
        admin_only(mess)
        result = deactivate_plugin(args)
        return result

    @botcmd
    def reload(self, mess, args):
        """reload a plugin"""
        admin_only(mess)
        result = deactivate_plugin(args) + " / " + activate_plugin(args)
        return result

    @botcmd
    def install(self, mess, args):
        """ install a plugin repository from the given source or a known public repo (see !repos to find those).
        for example from a known repo : !install err-codebot
        for example a git url : git@github.com:gbin/plugin.git
        or an url towards a tar.gz archive : http://www.gootz.net/plugin-latest.tar.gz
        """
        admin_only(mess)
        if not args.strip():
            return "You should have an urls/git repo argument"
        if args in KNOWN_PUBLIC_REPOS:
            args = KNOWN_PUBLIC_REPOS[args][0] # replace it by the url

        if args.endswith('tar.gz'):
            tar = TarFile(fileobj=urlopen(args))
            tar.extractall(path= PLUGIN_DIR)
            human_name = args.split('/')[-1][:-7]
        else:
            human_name = human_name_for_git_url(args)
            p = subprocess.Popen(['git', 'clone', args, human_name], cwd = PLUGIN_DIR, stdout = subprocess.PIPE, stderr = subprocess.PIPE)
            feedback = p.stdout.read()
            error_feedback = p.stderr.read()
            if p.wait():
               return "Could not load this plugin : \n%s\n---\n%s" % (feedback, error_feedback)
        self.add_plugin_repo(human_name, args)
        self.send(mess.getFrom(), "A new plugin repository named %s has been installed correctly from %s. Refreshing the plugins commands..." % (human_name, args), message_type=mess.getType())
        self.update_dynamic_plugins()
        self.activate_non_started_plugins()
        return "Plugin reload done."

    @botcmd
    def uninstall(self, mess, args):
        """ uninstall a plugin repository by name.
        """
        admin_only(mess)
        if not args.strip():
            return "You should have a repo name as argument"
        repos = self.internal_shelf.get('repos', {})
        if not repos.has_key(args):
            return "This repo is not installed check with !repos the list of installed ones"

        plugin_path = PLUGIN_DIR + os.sep + args
        for plugin in get_all_plugins():
            if plugin.path.startswith(plugin_path) and hasattr(plugin,'is_activated') and plugin.is_activated:
                self.send(mess.getFrom(), '/me is unloading plugin %s' % plugin.name)
                deactivate_plugin(plugin.name)

        shutil.rmtree(plugin_path)
        repos.pop(args)
        self.internal_shelf['repos'] = repos
        self.internal_shelf.sync()

        return 'Plugins unloaded and repo %s removed' % args


    @botcmd
    def repos(self, mess, args):
        """ list the current active plugin repositories
        """
        max_width = max([len(name) for name,(_,_) in KNOWN_PUBLIC_REPOS.iteritems()])
        answer = 'Public repos : \n' + '\n'.join(['%s  %s'%(name.ljust(max_width), desc) for name,(url,desc) in KNOWN_PUBLIC_REPOS.iteritems()])
        answer += '\n' + '-'* 40 + '\n\nInstalled repos :\n'
        repos = self.get_installed_plugin_repos()
        if not len(repos):
            answer += 'No plugin repo has been installed, use !install to add one.'
            return answer
        max_width = max([len(item[0]) for item in repos.iteritems()])
        answer+= '\n'.join(['%s -> %s' % (item[0].ljust(max_width), item[1]) for item in repos.iteritems()])
        return answer

    @botcmd
    def help(self, mess, args):
        """   Returns a help string listing available options.

        Automatically assigned to the "help" command."""
        if not args:
            description = 'Available commands:'

            clazz_commands = {}
            for (name, command) in self.commands.iteritems():
                clazz = get_class_that_defined_method(command)
                commands = clazz_commands.get(clazz, [])
                commands.append((name, command))
                clazz_commands[clazz] = commands

            usage = ''
            for clazz in sorted(clazz_commands):
                usage += '\n\n%s: %s\n' % (clazz.__name__, clazz.__doc__ or '')
                usage += '\n'.join(sorted([
                '\t!%s: %s' % (name, (command.__doc__ or\
                                    '(undocumented)').strip().split('\n', 1)[0])
                for (name, command) in clazz_commands[clazz] if name != 'help' and not command._jabberbot_command_hidden
                ]))
            usage += '\n\n'
        else:
            return super(ErrBot, self).help(mess,args)

        top = self.top_of_help_message()
        bottom = self.bottom_of_help_message()
        return ''.join(filter(None, [top, description, usage, bottom]))

    @botcmd
    def update(self, mess, args):
        """ update the bot and/or plugins
        use : !update all
        to update everything
        or : !update core
        to update only the core
        or : !update repo_name repo_name ...
        to update selectively some repos
        """
        admin_only(mess)
        directories = set()
        args = args.split(' ')
        repos = self.internal_shelf.get('repos', {})
        if 'all' in args or 'core' in args:
            directories.add(os.path.dirname(__file__))

        if 'all' in args:
            directories.update([PLUGIN_DIR+os.sep+name for name in repos])
        else:
            directories.update([PLUGIN_DIR+os.sep+name for name in set(args).intersection(set(repos))])

        for d in directories:
            self.send(mess.getFrom(), "I am updating %s ..." % d , message_type=mess.getType())
            p = subprocess.Popen(['git', 'pull'], cwd=d, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            feedback = p.stdout.read() + '\n' + '-'*50 + '\n'
            err = p.stderr.read().strip()
            if err:
                feedback += err + '\n' + '-'*50 + '\n'
            if p.wait():
                self.send(mess.getFrom(), "Update of %s failed...\n\n%s\n\n resuming..." % (d,feedback) , message_type=mess.getType())
            else:
                self.send(mess.getFrom(), "Update of %s succeeded...\n\n%s\n\n" % (d,feedback) , message_type=mess.getType())
        self.quit(-1337)
        return "Done, restarting"

    @botcmd
    def taillog(self, mess, args):
        """ Display a tail of the log
        use : !log
        """
        #admin_only(mess) # uncomment if paranoid.
        if BOT_LOG_FILE:
            with open(BOT_LOG_FILE, 'r') as f:
                return tail(f, 40)
        return 'No log is configured, please define BOT_LOG_FILE in config.py'

