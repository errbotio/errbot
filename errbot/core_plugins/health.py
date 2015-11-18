import gc
import os
import signal
from datetime import datetime

from errbot import BotPlugin, botcmd
from errbot.plugin_manager import global_restart
from errbot.utils import format_timedelta


class Health(BotPlugin):

    @botcmd(template='status')
    def status(self, mess, args):
        """ If I am alive I should be able to respond to this one
        """
        plugins_statuses = self.status_plugins(mess, args)
        loads = self.status_load(mess, args)
        gc = self.status_gc(mess, args)

        return {'plugins_statuses': plugins_statuses['plugins_statuses'],
                'loads': loads['loads'],
                'gc': gc['gc']}

    @botcmd(template='status_load')
    def status_load(self, mess, args):
        """ shows the load status
        """
        try:
            from posix import getloadavg
            loads = getloadavg()
        except Exception:
            loads = None

        return {'loads': loads}

    @botcmd(template='status_gc')
    def status_gc(self, mess, args):
        """ shows the garbage collection details
        """
        return {'gc': gc.get_count()}

    @botcmd(template='status_plugins')
    def status_plugins(self, mess, args):
        """ shows the plugin status
        """
        all_blacklisted = self._bot.get_blacklisted_plugin()
        all_loaded = self._bot.get_all_active_plugin_names()
        all_attempted = sorted([p.name for p in self._bot.all_candidates])
        plugins_statuses = []
        for name in all_attempted:
            if name in all_blacklisted:
                if name in all_loaded:
                    plugins_statuses.append(('BA', name))
                else:
                    plugins_statuses.append(('BD', name))
            elif name in all_loaded:
                plugins_statuses.append(('A', name))
            elif self._bot.get_plugin_obj_by_name(name) is not None and self._bot.get_plugin_obj_by_name(
                    name).get_configuration_template() is not None and self._bot.get_plugin_configuration(name) is None:
                plugins_statuses.append(('C', name))
            else:
                plugins_statuses.append(('D', name))

        return {'plugins_statuses': plugins_statuses}

    @botcmd
    def uptime(self, mess, args):
        """ Return the uptime of the bot
        """
        return "I've been up for %s %s (since %s)" % (args, format_timedelta(datetime.now() - self._bot.startup_time),
                                                      self._bot.startup_time.strftime('%A, %b %d at %H:%M'))

    # noinspection PyUnusedLocal
    @botcmd(admin_only=True)
    def restart(self, mess, args):
        """ Restart the bot. """
        self.send(mess.frm, "Deactivating all the plugins...")
        self._bot.deactivate_all_plugins()
        self.send(mess.frm, "Restarting")
        self._bot.shutdown()
        global_restart()
        return "I'm restarting..."

    # noinspection PyUnusedLocal
    @botcmd(admin_only=True)
    def killbot(self, mess, args):
        """ Shutdown the bot.
        Useful when the things are going crazy and you down have access to the machine.
        """
        if args != "really":
            return "Use `!killbot really` if you really want to shutdown the bot."

        self.send(mess.frm, "Dave, I can see you are really upset about this...")
        self._bot.deactivate_all_plugins()
        self.send(mess.frm, "I know I have made some very poor decisions recently...")
        self.send(mess.frm, "Daisy, Daaaaiseey...")
        self._bot.shutdown()
        self.log.debug("Exiting")
        os.kill(os.getpid(), signal.SIGTERM)
