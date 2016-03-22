import io
from errbot import BotPlugin, botcmd
from errbot.flow import Node, Flow





class Utils(BotPlugin):

    def recurse_node(self, response: io.StringIO, stack, f:Node):
        if f in stack:
            response.write("%s⥀\n" % ("\t" * len(stack)))
            return
        if isinstance(f, Flow):
            response.write("Flow " + f.name + ": " + f.description + "\n")
        else:
            cmd = self._bot.commands[f.command]
            response.write("%s⤷%s: %s\n" % ("\t" * len(stack), f, cmd.__doc__))
        for _, sf in f.children:
            self.recurse_node(response, stack + [f], sf)

    # noinspection PyUnusedLocal
    @botcmd
    def flows(self, mess, args):
        """ Displays the list of setup flows.
        """
        with io.StringIO() as response:
            if args:
                flow = self._bot.flow_executor.flows.get(args, None)
                if flow is None:
                    return "Flow %s doesn't exist." % args
                self.recurse_node(response, [], flow)
            else:
                for name, flow in self._bot.flow_executor.flows.items():
                    response.write(name + ": " + flow.description + "\n")
            return response.getvalue()

