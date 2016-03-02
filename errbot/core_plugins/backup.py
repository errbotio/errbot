import os

from errbot import BotPlugin, botcmd


class Backup(BotPlugin):
    """ Backup related commands. """
    @botcmd(admin_only=True)
    def backup(self, msg, args):
        """Backup everything.
           Makes a backup script called backup.py in the data bot directory.
           You can restore the backup from the command line with err.py --restore
        """
        filename = os.path.join(self.bot_config.BOT_DATA_DIR, 'backup.py')
        with open(filename, 'w') as f:
            f.write('## This file is not executable on its own. use err.py -r FILE to restore your bot.\n\n')
            f.write('log.info("Restoring core configs.")\n')
            for key in self._bot:  # don't mimic that in real plugins, this is core only.
                f.write('bot["'+key+'"] = ' + repr(self._bot[key]) + '\n')

            f.write('log.info("Installing plugins.")\n')
            f.write('if "repos" in bot:\n')
            f.write('  for repo in bot["repos"]:\n')
            f.write('    errors = bot.install_repo(repo)\n')
            f.write('    for error in errors:\n')
            f.write('      log.error(error)\n')

            f.write('log.info("Restoring plugins data.")\n')

            for plug in self._bot.getAllPlugins():
                pobj = plug.plugin_object
                if pobj.shelf:
                    f.write('pobj = bot.get_plugin_by_name("' + plug.name + '").plugin_object\n')
                    f.write('pobj.init_storage()\n')

                    for key in pobj.shelf:
                        f.write('pobj["'+key+'"] = ' + repr(pobj[key]) + '\n')
                    f.write('pobj.close_storage()\n')

        return "The backup file has been written in '%s'" % filename

    @botcmd(admin_only=True)
    def backupv4(self, msg, args):
        """Backup everything.
           Makes a backup script called backup.py in the data bot directory.
           You can restore the backup from the command line with err.py --restore
        """
        filename = os.path.join(self.bot_config.BOT_DATA_DIR, 'backupv4.py')
        with open(filename, 'w') as f:
            f.write('## This file is not executable on its own. use errbot -r FILE to restore your bot.\n\n')
            f.write('log.info("Restoring repo_manager.")\n')
            f.write('bot.repo_manager["installed_repos"] = ' + repr(self._bot['repos']) + '\n')

            f.write('log.info("Installing plugins.")\n')
            f.write('for repo in bot.repo_manager["installed_repos"].values():\n')
            f.write('  log.error(bot.repo_manager.install_repo(repo))\n')

            f.write('log.info("Restoring plugins data.")\n')
            f.write('bot.plugin_manager.update_dynamic_plugins()\n')
            for plug in self._bot.getAllPlugins():
                pobj = plug.plugin_object
                if pobj.shelf:
                    f.write('pobj = bot.plugin_manager.get_plugin_by_name("' + plug.name + '").plugin_object\n')
                    f.write('pobj.init_storage()\n')

                    for key, value in pobj.items():
                        f.write('pobj["'+key+'"] = ' + repr(value) + '\n')
                    f.write('pobj.close_storage()\n')

        return "The backup file has been written in '%s'" % filename
