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
            f.write('## This file is not executable on its own. use errbot -r FILE to restore your bot.\n\n')
            f.write('log.info("Restoring repo_manager.")\n')
            for key, value in self._bot.repo_manager.items():
                f.write('bot.repo_manager["'+key+'"] = ' + repr(value) + '\n')
            f.write('log.info("Restoring plugin_manager.")\n')
            for key, value in self._bot.plugin_manager.items():  # don't mimic that in real plugins, this is core only.
                f.write('bot.plugin_manager["'+key+'"] = ' + repr(value) + '\n')

            f.write('log.info("Installing plugins.")\n')
            f.write('if "installed_repos" in bot.repo_manager:\n')
            f.write('  for repo in bot.repo_manager["installed_repos"]:\n')
            f.write('    log.error(bot.repo_manager.install_repo(repo))\n')

            f.write('log.info("Restoring plugins data.")\n')
            f.write('bot.plugin_manager.update_dynamic_plugins()\n')
            for plug in self._bot.plugin_manager.getAllPlugins():
                pobj = plug.plugin_object
                if pobj._store:
                    f.write('pobj = bot.plugin_manager.get_plugin_by_name("' + plug.name + '").plugin_object\n')
                    f.write('pobj.init_storage()\n')

                    for key, value in pobj.items():
                        f.write('pobj["'+key+'"] = ' + repr(value) + '\n')
                    f.write('pobj.close_storage()\n')

        return "The backup file has been written in '%s'" % filename
