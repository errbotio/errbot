import io
import json

from errbot import BotPlugin, botcmd, arg_botcmd
from errbot.flow import FlowNode, FlowRoot, Flow, FLOW_END
from errbot.core_plugins.acls import glob, get_acl_usr


class Flows(BotPlugin):
    """ Management commands related to flows / conversations.
    """

    def recurse_node(self, response: io.StringIO, stack, f: FlowNode, flow: Flow = None):
        if f in stack:
            response.write(f'{"&emsp;&nbsp;" * (len(stack))}↺<br>')
            return
        if isinstance(f, FlowRoot):
            doc = f.description if flow else ''
            response.write('Flow [' + f.name + '] ' + doc + ' <br>')
            if flow and flow.current_step == f:
                response.write(f'↪&nbsp;&nbsp;Start (_{flow.requestor}_)<br>')
        else:
            cmd = 'END' if f is FLOW_END else self._bot.all_commands[f.command]
            requestor = f'(_{str(flow.requestor)}_)' if flow and flow.current_step == f else ''
            doc = cmd.__doc__ if flow and f is not FLOW_END else ''
            response.write(f'{"&emsp;&nbsp;" * len(stack)}'
                           f'↪&nbsp;&nbsp;**{f if f is not FLOW_END else "END"}** {doc if doc else ""} {requestor}<br>')
        for _, sf in f.children:
            self.recurse_node(response, stack + [f], sf, flow)

    @botcmd(syntax='<name>')
    def flows_show(self, _, args):
        """ Shows the structure of a flow.
        """
        if not args:
            return 'You need to specify a flow name.'
        with io.StringIO() as response:
            flow_node = self._bot.flow_executor.flow_roots.get(args, None)
            if flow_node is None:
                return f"Flow {args} doesn't exist."
            self.recurse_node(response, [], flow_node)
            return response.getvalue()

    # noinspection PyUnusedLocal
    @botcmd
    def flows_list(self, msg, args):
        """ Displays the list of setup flows.
        """
        with io.StringIO() as response:
            for name, flow_node in self._bot.flow_executor.flow_roots.items():
                if flow_node.description:
                    response.write("- **" + name + "** " + flow_node.description + "\n")
                else:
                    response.write("- **" + name + "** " + "No description" + "\n")
            return response.getvalue()

    @botcmd(split_args_with=' ', syntax='<name> [initial_payload]')
    def flows_start(self, msg, args):
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
                return f'Cannot parse json {json_payload}: {e}.'
        self._bot.flow_executor.start_flow(flow_name, msg.frm, context)
        return f'Flow **{flow_name}** started ...'

    @botcmd()
    def flows_status(self, msg, args):
        """ Displays the list of started flows.
        """
        with io.StringIO() as response:
            if not self._bot.flow_executor.in_flight:
                response.write('No Flow started.\n')

            else:
                if not [flow for flow in self._bot.flow_executor.in_flight if self.check_user(msg, flow)]:
                    response.write(f'No Flow started for current user: {get_acl_usr(msg)}.\n')

                else:
                    if args:
                        for flow in self._bot.flow_executor.in_flight:
                            if self.check_user(msg, flow):
                                if flow.name == args:
                                    self.recurse_node(response, [], flow.root, flow)

                    else:
                        for flow in self._bot.flow_executor.in_flight:
                            if self.check_user(msg, flow):
                                next_steps = [f'\\*{str(step[1].command)}\\*' for step in
                                              flow._current_step.children if step[1].command]
                                next_steps_str = '\n'.join(next_steps)
                                text = f'\\>>> {str(flow.requestor)} is using flow \\*{flow.name}\\* on step ' \
                                       f'\\*{flow.current_step}\\*\nNext Step(s): \n{next_steps_str}'
                                response.write(text)
            return response.getvalue()

    @botcmd(syntax='[flow_name]')
    def flows_stop(self, msg, args):
        """ Stop flows you are in.
        optionally, stop a specific flow you are in.
        """
        if args:
            flow = self._bot.flow_executor.stop_flow(args, msg.frm)
            if flow:
                yield flow.name + ' stopped.'
                return
            yield 'Flow not found.'
            return

        one_stopped = False
        for flow in self._bot.flow_executor.in_flight:
            if flow.requestor == msg.frm:
                flow = self._bot.flow_executor.stop_flow(flow.name, msg.frm)
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

    def check_user(self, msg, flow):
        """Checks to make sure that either the user started the flow, or is a bot admin
        """
        if glob(get_acl_usr(msg), self.bot_config.BOT_ADMINS):
            return True
        elif glob(get_acl_usr(msg), flow.requestor.person):
            return True
        return False
