import logging
from collections import MutableMapping, Iterable
from typing import Mapping, Union, List

from threadpool import ThreadPool, WorkRequest
from yapsy.IPlugin import IPlugin

from errbot import Message
from errbot.backends.base import Identifier

log = logging.getLogger(__name__)


class FlowNode(object):
    def __init__(self, command=None):  # None = start node
        self.command = command
        self.children = []  # (predicate, node)

    def connect(self, node_or_command, predicate):
        node_to_connect_to = node_or_command if isinstance(node_or_command, FlowNode) else FlowNode(node_or_command)
        self.children.append((predicate, node_to_connect_to))
        return node_to_connect_to

    def predicate_for_node(self, node):
        for predicate, possible_node in self.children:
            if node == possible_node:
                return predicate
        return None

    def __str__(self):
        return self.command


class FlowRoot(FlowNode):
    """
    This represent the entry point of a flow description.
    """
    def __init__(self, flow_name: str, description: str):
        """

        :param flow_name: The name of the conversation/flow.
        :param description:  A human description of what this flow does.
        """
        super().__init__()
        self.flow_name = flow_name
        self.description = description
        self.auto_triggers = []

    def connect(self, node_or_command, predicate, auto_trigger=False):
        resp = super().connect(node_or_command, predicate)
        if auto_trigger:
            self.auto_triggers.append(node_or_command)
        return resp

    def __str__(self):
        return self.flow_name


class InvalidState(Exception):
    pass


class Flow(object):
    def __init__(self, root: FlowRoot, requestor: Identifier, initial_context):
        self._root = root
        self._current_step = self._root
        self.ctx = dict(initial_context)
        self.requestor = requestor

    def execute(self):
        return self._current_step.command(self.ctx, None)

    def next_autosteps(self) -> List[FlowNode]:
        return [node for predicate, node in self._current_step.children if predicate(self.ctx)]

    def next_steps(self) -> List[FlowNode]:
        return [node for predicate, node in self._current_step.children]

    def advance(self, next_step: FlowNode, enforce_predicate=True):
        if enforce_predicate:
            predicate = self._current_step.predicate_for_node(next_step)
            if predicate is None:
                raise ValueError("There is no such children: %s" % next_step)

            if not predicate(self.ctx):
                raise InvalidState("It is not possible to advance to this step because its predicate is false")

        self._current_step = next_step
        # TODO: error / success predicates

    def __str__(self):
        return "FlowInstance of %s (%s) with params %s" % (self._root, self.ctx.frm, dict(self.ctx))


class BotFlow(IPlugin):
    def __init__(self, bot):
        super().__init__()
        self._bot = bot
        self.is_activated = False

    def activate(self) -> None:
        """
            Override if you want to do something at initialization phase (don't forget to
            super(Gnagna, self).activate())
        """
        self._bot.inject_flows_from(self)
        self.is_activated = True

    def deactivate(self) -> None:
        """
            Override if you want to do something at tear down phase (don't forget to super(Gnagna, self).deactivate())
        """
        self._bot.remove_flows_from(self)
        self.is_activated = False

    def get_command(self, command_name: str):
        self._bot.commands.get(command_name, None)


class FlowExecutor(object):
    """
    This is a instance that can monitor and execute flow instances.
    """
    def __init__(self, bot):
        self.flow_roots = {}
        self.in_flight = []
        self._pool = ThreadPool(5)
        self._bot = bot

    def add_flow(self, flow: FlowRoot):
        self.flow_roots[flow.flow_name] = flow

    def trigger(self, cmd:str, requestor: Identifier) -> str:
        """
        Trigger workflows that may have command cmd as a auto_trigger.
        This assume cmd has been correctly executed.
        :param requestor: the identifier of the person who started this flow
        :param cmd: the command that has just been executed.
        :returns: The name of the worflow it triggered or None if none were matching.
        """
        log.debug("Test if the command %s is an auto-trigger for any flow ...",  cmd)
        for name, flow_root in self.flow_roots.items():
            if cmd in flow_root.auto_triggers:
                log.debug("Flow %s has been auto-triggered by the command %s by user %s", name, cmd, requestor)
                self._trigger_flow(flow_root, requestor, cmd)

    def _trigger_flow(self, flow_root, requestor: Identifier, initial_command):
        empty_context = {}
        flow = Flow(flow_root, requestor, empty_context)
        for possible_next_step in flow.next_steps():
            if possible_next_step.command == initial_command:
                # The predicate is good as we just executed manually the command.
                flow.advance(possible_next_step, enforce_predicate=False)
                self._enqueue_flow(flow)
                break

    def start_flow(self, name: str, requestor: Identifier, initial_context: Mapping):
        if name not in self.flow_roots:
            raise ValueError("Flow %s doesn't exist" % name)
        self._enqueue_flow(Flow(self.flow_roots[name], requestor, initial_context))

    def _enqueue_flow(self, flow):
        self.in_flight.append(flow)
        self._pool.putRequest(WorkRequest(self.execute, args=(flow, )))

    def execute(self, flow: Flow):
        while True:
            autosteps = flow.next_autosteps()

            if not autosteps:
                log.debug("Flow: Nothing left to do.")
                break

            steps = flow.next_steps()
            # !flows start poll_setup {\"title\":\"yeah!\",\"options\":[\"foo\",\"bar\",\"baz\"]}
            log.debug("Steps triggered automatically %s", ', '.join(str(node) for node in autosteps))
            log.debug("All possible next steps: %s", ', '.join(str(node) for node in steps))

            for autostep in autosteps:
                log.debug("Proceeding automatically with step %s", autostep)
                try:
                    msg = Message(frm=flow.requestor, flow=flow)
                    result = self._bot.commands[autostep.command](msg, None)
                    log.debug('Step result %s: %s', flow.requestor, result)

                except Exception as e:
                    log.exception('%s errored at %s', flow, autostep)
                    self._bot.send(flow.requestor,
                                   '%s errored at %s with "%s"' % (flow, autostep, e))
                flow.advance(autostep)  # TODO: this is only true for a single step, make it forkable.
