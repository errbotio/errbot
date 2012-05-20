#!/usr/bin/python
# -*- coding: utf-8 -*-
import logging
import os
import shelve
import shutil
import subprocess
from tarfile import TarFile
from urllib2 import urlopen
from config import BOT_DATA_DIR, BOT_ADMINS

from jabberbot import JabberBot, botcmd
from plugin_manager import get_all_active_plugin_names, activate_plugin, deactivate_plugin, activate_all_plugins, deactivate_all_plugins, update_plugin_places, init_plugin_manager
from utils import get_jid_from_message, PLUGINS_SUBDIR

PLUGIN_DIR = BOT_DATA_DIR + os.sep + PLUGINS_SUBDIR

def admin_only(mess):
    if mess.getType() == 'groupchat':
        raise Exception('You cannot administer the bot from a chatroom, message the bot directly')
    usr = get_jid_from_message(mess)
    if usr not in BOT_ADMINS:
        raise Exception('You cannot administer the bot from this user %s.' % usr)

class ErrBot(JabberBot):
    MSG_ERROR_OCCURRED = 'Computer says nooo. '
    MSG_UNKNOWN_COMMAND = 'Unknown command: "%(command)s". '
    shelf = shelve.DbfilenameShelf(BOT_DATA_DIR + os.sep + 'core.db')
    def add_repo(self, name, url):
        repos = self.shelf.get('repos', {})
        repos[name] = url
        self.shelf['repos'] = repos
        self.shelf.sync()

    # this will load the plugins the admin has setup at runtime
    def update_dynamic_plugins(self):
        update_plugin_places([PLUGIN_DIR + os.sep + d for d in self.shelf.get('repos', {}).keys()])

    def __init__(self, instance_name, username, password, res=None, debug=False,
                 privatedomain=False, acceptownmsgs=False, handlers=None):
        self.instance_name = instance_name # can be use to distinguish rooms for example
        JabberBot.__init__(self, username, password, res, debug, privatedomain, acceptownmsgs, handlers)
        self.update_dynamic_plugins()

    def callback_message(self, conn, mess):
        for cls in ErrBot.__bases__:
            if hasattr(cls, 'callback_message'):
                try:
                    cls.callback_message(self, conn, mess)
                except:
                    logging.exception("Probably a type error")

    def activate_non_started_plugins(self):
        logging.info('Activating all the plugins...')
        activate_all_plugins()
        logging.info('Refreshing command list...')
        self.refresh_command_list()

    def signal_connect_to_all_plugins(self):
        for cls in ErrBot.__bases__:
            if hasattr(cls, 'callback_connect'):
                try:
                    cls.callback_connect(self)
                except:
                    logging.exception("callback_connect failed for %s" % cls)
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
        self.shelf.close()
        logging.info('Bye.')

    @botcmd
    def status(self, mess, args):
        """ If I am alive I should be able to respond to this one
        """
        return 'I am alive with those plugins :\n' + '\n'.join(get_all_active_plugin_names())

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
        self.refresh_command_list()
        return result

    @botcmd
    def unload(self, mess, args):
        """unload a plugin"""
        admin_only(mess)
        result = deactivate_plugin(args)
        self.refresh_command_list()
        return result

    @botcmd
    def reload(self, mess, args):
        """reload a plugin"""
        admin_only(mess)
        result = deactivate_plugin(args) + " / " + activate_plugin(args)
        self.refresh_command_list()
        return result

    @botcmd
    def install(self, mess, args):
        """ install a plugin repository from the given source.
        for example a git url : git@github.com:gbin/plugin.git
        or an url towards a tar.gz archive : http://www.gootz.net/plugin-latest.tar.gz
        """
        admin_only(mess)
        if not args.strip():
            return "You should have an urls/git repo argument"
        if args.endswith('tar.gz'):
            tar = TarFile(fileobj=urlopen(args))
            tar.extractall(path= PLUGIN_DIR)
            human_name = args.split('/')[-1][:-7]
        else:
            # try to humanize the last part of the git url as much as we can
            s = args.split('/')
            last_part = s[-1] if s[-1] else s[-2]
            human_name = last_part[:-4] if last_part.endswith('.git') else last_part
            p = subprocess.Popen(['git', 'clone', args, human_name], cwd = PLUGIN_DIR, stdout = subprocess.PIPE, stderr = subprocess.PIPE)
            feedback = p.stdout.read()
            error_feedback = p.stderr.read()
            if p.wait():
               return "Could not load this plugin : \n%s\n---\n%s" % (feedback, error_feedback)
        self.add_repo(human_name, args)
        self.send(mess.getFrom(), "A new plugin repository named %s has been installed correctly from %s. Refreshing the plugins commands..." % (human_name, args), message_type=mess.getType())
        self.update_dynamic_plugins()
        self.activate_non_started_plugins()
        return "Plugin reload done."

    @botcmd
    def uninstall(self, mess, args):
        """ install a plugin repository by name.
        """
        admin_only(mess)
        if not args.strip():
            return "You should have a repo name as argument"
        repos = self.shelf.get('repos', {})
        if not repos.has_key(args):
            return "This repo is not installed check with !repos the list of installed ones"
        shutil.rmtree(PLUGIN_DIR + os.sep + args)
        repos.pop(args)
        self.shelf['repos'] = repos
        self.shelf.sync()
        self.send(mess.getFrom(), "Deactivating all the plugins..." , message_type=mess.getType())
        ErrBot.__bases__ = (JabberBot, ) # violently remove all the commands
        init_plugin_manager() # violently zap the entire plugin system
        self.update_dynamic_plugins() # update the plugin places
        self.activate_non_started_plugins() # restart everything
        self.send(mess.getFrom(), "Restarting the plugins..." , message_type=mess.getType())
        self.signal_connect_to_all_plugins() # resignal them we are connected
        return 'Uninstall done'

    @botcmd
    def repos(self, mess, args):
        """ list the current active plugin repositories
        """
        admin_only(mess)
        repos = self.shelf.get('repos', {})
        if not len(repos):
            return 'No plugin repo has been installed, use !install to add one.'
        return 'Current plugins repos : \n' + '\n'.join(['%s\t-> %s'%item for item in repos.iteritems()]  )

    @botcmd
    def upgrade(self, mess, args):
        """ upgrade the bot """
        admin_only(mess)
        p = subprocess.Popen(['git', 'pull'], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        feedback = p.stdout.read()
        error_feedback = p.stderr.read()

        if not p.wait():
            self.quit(-1337)
            return "Auto upgrade myself done :), gonna restart now... \n" + feedback + "\n\n----- \n\n" + error_feedback
        else:
            return "Auto upgrade from git failed, somebody probably does something wrong on my place\n " + feedback + "\n\n----- \n\n" + error_feedback




