# -*- coding: utf-8 -*-
import io
import json

from errbot import BotPlugin, botcmd, arg_botcmd
from errbot.flow import FlowNode, FlowRoot, Flow, FLOW_END


class Flows(BotPlugin):
    """ Management commands related to flows / conversations.
    """

    def recurse_node(self, response: io.StringIO, stack, f: FlowNode, flow: Flow=None):
        if f in stack:
            response.write('%s↺<br>' % ('&emsp;&nbsp;' * (len(stack))))
            return
        if isinstance(f, FlowRoot):
            doc = f.description if flow else ''
            response.write('Flow [' + f.name + '] ' + doc + ' <br>')
            if flow and flow.current_step == f:
                response.write('↪&nbsp;&nbsp;Start (_%s_)<br>' % str(flow.requestor))
        else:
            cmd = 'END' if f is FLOW_END else self._bot.all_commands[f.command]
            requestor = '(_%s_)' % str(flow.requestor) if flow and flow.current_step == f else ''
            doc = cmd.__doc__ if flow and f is not FLOW_END else ''
            response.write('%s↪&nbsp;&nbsp;**%s** %s %s<br>' % ('&emsp;&nbsp;' * len(stack),
                           f if f is not FLOW_END else 'END', doc if doc else '', requestor))
        for _, sf in f.children:
            self.recurse_node(response, stack + [f], sf, flow)

    @botcmd(syntax='<name>')
    def flows_show(self, _, args):
        """ Shows the structure of a flow.
        """
        if not args:
            return "You need to specify a flow name."
        with io.StringIO() as response:
            flow_node = self._bot.flow_executor.flow_roots.get(args, None)
            if flow_node is None:
                return "Flow %s doesn't exist." % args
            self.recurse_node(response, [], flow_node)
            return response.getvalue()

    # noinspection PyUnusedLocal
    @botcmd
    def flows_list(self, mess, args):
        """ Displays the list of setup flows.
        """
        with io.StringIO() as response:
            for name, flow_node in self._bot.flow_executor.flow_roots.items():
                response.write("- **" + name + "** " + flow_node.description + "\n")
            return response.getvalue()

    @botcmd(split_args_with=' ', syntax='<name> [initial_payload]')
    def flows_start(self, mess, args):
        """ Manually start a flow within the context of the calling user.
        You can prefeed the flow data with a json payload.
        Example:
             !flows start poll_setup {"title":"yeah!","options":["foo","bar","baz"]}
        """
        if not args:
            return 'You need to specify a flow to manually start'

        context = {}
        flow_name = args[0]
        if len(args) > 1:
            json_payload = ' '.join(args[1:])
            try:
                context = json.loads(json_payload)
            except Exception as e:
                return 'Cannot parse json %s: %s' % (json_payload, e)
        self._bot.flow_executor.start_flow(flow_name, mess.frm, context)
        return 'Flow **%s** started ...' % flow_name

    @botcmd(admin_only=True)
    def flows_status(self, mess, args):
        """ Displays the list of started flows.
        """
        with io.StringIO() as response:
            if args:
                for flow in self._bot.flow_executor.in_flight:
                    if flow.name == args:
                        self.recurse_node(response, [], flow.root, flow)
            else:
                if not self._bot.flow_executor.in_flight:
                    response.write('No Flow started.\n')
                else:
                    for flow in self._bot.flow_executor.in_flight:
                        response.write('**' + flow.name + "** " + str(flow.requestor) + '\n')
            return response.getvalue()

    @botcmd(syntax='[flow_name]')
    def flows_stop(self, mess, args):
        """ Stop flows you are in.
        optionally, stop a specific flow you are in.
        """
        if args:
            flow = self._bot.flow_executor.stop_flow(args, mess.frm)
            if flow:
                yield flow.name + ' stopped.'
                return
            yield 'Flow not found.'
            return

        one_stopped = False
        for flow in self._bot.flow_executor.in_flight:
            if flow.requestor == mess.frm:
                flow = self._bot.flow_executor.stop_flow(flow.name, mess.frm)
                if flow:
                    one_stopped = True
                    yield flow.name + ' stopped.'
        if not one_stopped:
            yield 'No Flow found.'

    @arg_botcmd('flow_name', type=str)
    @arg_botcmd('user', type=str)
    def flows_kill(self, _, user, flow_name):
        """ Admin command to kill a specific flow."""
        flow = self._bot.flow_executor.stop_flow(flow_name, self.build_identifier(user))
        if flow:
            return flow.name + ' killed.'
        return 'Flow not found.'
