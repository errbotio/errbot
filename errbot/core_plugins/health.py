import gc
import os
import signal

from datetime import datetime
from errbot import BotPlugin, botcmd, arg_botcmd
from errbot.utils import format_timedelta, global_restart


class Health(BotPlugin):
    @botcmd(template='status')
    def status(self, msg, args):
        """ If I am alive I should be able to respond to this one
        """
        plugins_statuses = self.status_plugins(msg, args)
        loads = self.status_load(msg, args)
        gc = self.status_gc(msg, args)

        return {'plugins_statuses': plugins_statuses['plugins_statuses'],
                'loads': loads['loads'],
                'gc': gc['gc']}

    @botcmd(template='status_load')
    def status_load(self, _, args):
        """ shows the load status
        """
        try:
            from posix import getloadavg
            loads = getloadavg()
        except Exception:
            loads = None

        return {'loads': loads}

    @botcmd(template='status_gc')
    def status_gc(self, _, args):
        """ shows the garbage collection details
        """
        return {'gc': gc.get_count()}

    @botcmd(template='status_plugins')
    def status_plugins(self, _, args):
        """ shows the plugin status
        """
        pm = self._bot.plugin_manager
        all_blacklisted = pm.get_blacklisted_plugin()
        all_loaded = pm.get_all_active_plugin_names()
        all_attempted = sorted(pm.plugin_infos.keys())
        plugins_statuses = []
        for name in all_attempted:
            if name in all_blacklisted:
                if name in all_loaded:
                    plugins_statuses.append(('BA', name))
                else:
                    plugins_statuses.append(('BD', name))
            elif name in all_loaded:
                plugins_statuses.append(('A', name))
            elif pm.get_plugin_obj_by_name(name) is not None \
                    and pm.get_plugin_obj_by_name(name).get_configuration_template() is not None \
                    and pm.get_plugin_configuration(name) is None:
                plugins_statuses.append(('C', name))
            else:
                plugins_statuses.append(('D', name))

        return {'plugins_statuses': plugins_statuses}

    @botcmd
    def uptime(self, _, args):
        """ Return the uptime of the bot
        """
        u = format_timedelta(datetime.now() - self._bot.startup_time)
        since = self._bot.startup_time.strftime('%A, %b %d at %H:%M')
        return f"I've been up for {u} (since {since})."

    # noinspection PyUnusedLocal
    @botcmd(admin_only=True)
    def restart(self, msg, args):
        """ Restart the bot. """
        self.send(msg.frm, "Deactivating all the plugins...")
        self._bot.plugin_manager.deactivate_all_plugins()
        self.send(msg.frm, "Restarting")
        self._bot.shutdown()
        global_restart()
        return "I'm restarting..."

    # noinspection PyUnusedLocal
    @arg_botcmd('--confirm', dest="confirmed", action="store_true",
                help="confirm you want to shut down", admin_only=True)
    @arg_botcmd('--kill', dest="kill", action="store_true",
                help="kill the bot instantly, don't shut down gracefully", admin_only=True)
    def shutdown(self, msg, confirmed, kill):
        """
        Shutdown the bot.

        Useful when the things are going crazy and you don't have access to the machine.
        """
        if not confirmed:
            yield "Please provide `--confirm` to confirm you really want me to shut down."
            return

        if kill:
            yield "Killing myself right now!"
            os.kill(os.getpid(), signal.SIGKILL)
        else:
            yield "Roger that. I am shutting down."
            os.kill(os.getpid(), signal.SIGINT)
