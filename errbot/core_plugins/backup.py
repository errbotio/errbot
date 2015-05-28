from errbot import BotPlugin, botcmd
from errbot.holder import bot
from errbot.plugin_manager import get_all_plugins
import os

class Backup(BotPlugin):
  @botcmd
  def backup(self, msg, args):
    """Backup everything.
       Makes a backup script called backup.py in the data bot directory.
    """
    filename = os.path.join(self.bot_config.BOT_DATA_DIR, 'backup.py')
    with open(filename, 'w') as f:
      f.write('from errbot.holder import bot\n')
      f.write('from errbot.plugin_manager import get_plugin_by_name\n\n')
      for key in bot:
        f.write('bot["'+key+'"] = ' + repr(bot[key]) + '\n')
      for plug in get_all_plugins():
        pobj = plug.plugin_object
        if pobj.shelf:
          f.write('pobj = get_plugin_by_name("' + plug.name + '").plugin_object\n')
          for key in pobj.shelf:
            f.write('pobj["'+key+'"] = ' + repr(pobj[key]) + '\n')


    return "The backup file has been writen in '%s'" % filename


