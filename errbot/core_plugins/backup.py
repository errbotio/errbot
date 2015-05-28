from errbot import BotPlugin, botcmd
from errbot.holder import bot
from errbot.plugin_manager import get_all_plugins
import os

class Backup(BotPlugin):
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
      for key in bot:
        f.write('bot["'+key+'"] = ' + repr(bot[key]) + '\n')

      f.write('log.info("Installing plugins.")\n')
      f.write('for repo in bot["repos"]:\n')
      f.write('   errors = bot.install(repo)\n')
      f.write('   for error in errors:\n')
      f.write('      log.error(error)\n')

      f.write('log.info("Restoring plugins data.")\n')

      for plug in get_all_plugins():
        pobj = plug.plugin_object
        if pobj.shelf:
          f.write('pobj = get_plugin_by_name("' + plug.name + '").plugin_object\n')
          f.write('pobj.init_storage()\n')

          for key in pobj.shelf:
            f.write('pobj["'+key+'"] = ' + repr(pobj[key]) + '\n')
          f.write('pobj.close_storage()\n')


    return "The backup file has been writen in '%s'" % filename

