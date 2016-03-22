from errbot import BotPlugin, botcmd


class Utils(BotPlugin):

    # noinspection PyUnusedLocal
    @botcmd
    def flows(self, mess, args):
        """ Displays the list of setup flows.
        """
        response = ""
        for name, flow in self._bot.flow_executor.flows.items():
            response += name + ": " + flow.description + "\n"
        return response

