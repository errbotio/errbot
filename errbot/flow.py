import logging
from threading import RLock
from typing import Mapping, List, Tuple

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
    def __init__(self, name: str, description: str):
        """

        :param name: The name of the conversation/flow.
        :param description:  A human description of what this flow does.
        """
        super().__init__()
        self.name = name
        self.description = description
        self.auto_triggers = []

    def connect(self, node_or_command, predicate, auto_trigger=False):
        resp = super().connect(node_or_command, predicate)
        if auto_trigger:
            self.auto_triggers.append(node_or_command)
        return resp

    def __str__(self):
        return self.name


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

    @property
    def name(self):
        return self._root.name

    def __str__(self):
        return "%s (%s) with params %s" % (self._root, self.requestor, dict(self.ctx))


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
        self._lock = RLock()
        self.flow_roots = {}
        self.in_flight = []
        self._pool = ThreadPool(5)
        self._bot = bot

    def add_flow(self, flow: FlowRoot):
        with self._lock:
            self.flow_roots[flow.name] = flow

    def get_context_for_flows(self, cmd: str, requestor: Identifier) -> str:
        """
        This should be called before resuming a flow with a specific command to get the context for the command input.
        """

    def trigger(self, cmd: str, requestor: Identifier, extra_context=None) -> Flow:
        """
        Trigger workflows that may have command cmd as a auto_trigger or an in flight flow waiting for command.
        This assume cmd has been correctly executed.
        :param requestor: the identifier of the person who started this flow
        :param cmd: the command that has just been executed.
        :param extra_context: extra context from the current conversation
        :returns: The flow it triggered or None if none were matching.
        """
        flow, next_step = self.check_inflight_flow_triggered(cmd, requestor)
        if not flow:
            flow, next_step = self._check_if_new_flow_is_triggered(cmd, requestor)
        if not flow:
            return None

        flow.advance(next_step, enforce_predicate=False)
        if extra_context:
            flow.ctx = dict(extra_context)
        self._enqueue_flow(flow)
        return flow

    def check_inflight_flow_triggered(self, cmd: str, requestor: Identifier) -> Tuple[Flow, FlowNode]:
        log.debug("Test if the command %s is a trigger for an inflight flow ...", cmd)
        # TODO: What if 2 flows wait for the same command ?
        with self._lock:
            for flow in self.in_flight:
                if flow.requestor == requestor:
                    log.debug("Requestor has a flow %s in flight", flow.name)
                    for next_step in flow.next_steps():
                        if next_step.command == cmd:
                            log.debug("Requestor has a flow in flight waiting for this command !")
                            return flow, next_step
        log.debug("None matched.")
        return None, None

    def _check_if_new_flow_is_triggered(self, cmd: str, requestor: Identifier) -> Tuple[Flow, FlowNode]:
        """
        Trigger workflows that may have command cmd as a auto_trigger..
        This assume cmd has been correctly executed.
        :param requestor: the identifier of the person who started this flow
        :param cmd: the command that has just been executed.
        :returns: The name of the flow it triggered or None if none were matching.
        """
        log.debug("Test if the command %s is an auto-trigger for any flow ...",  cmd)
        with self._lock:
            for name, flow_root in self.flow_roots.items():
                if cmd in flow_root.auto_triggers:
                    log.debug("Flow %s has been auto-triggered by the command %s by user %s", name, cmd, requestor)
                    return self._create_new_flow(flow_root, requestor, cmd)
        return None, None

    @staticmethod
    def _create_new_flow(flow_root, requestor: Identifier, initial_command) -> Tuple[Flow, FlowNode]:
        empty_context = {}
        flow = Flow(flow_root, requestor, empty_context)
        for possible_next_step in flow.next_steps():
            if possible_next_step.command == initial_command:
                # The predicate is good as we just executed manually the command.
                return flow, possible_next_step
        return None, None

    def start_flow(self, name: str, requestor: Identifier, initial_context: Mapping) -> Flow:
        if name not in self.flow_roots:
            raise ValueError("Flow %s doesn't exist" % name)
        flow = Flow(self.flow_roots[name], requestor, initial_context)
        self._enqueue_flow(flow)
        return flow

    def _enqueue_flow(self, flow):
        with self._lock:
            if flow not in self.in_flight:
                self.in_flight.append(flow)
        self._pool.putRequest(WorkRequest(self.execute, args=(flow, )))

    def execute(self, flow: Flow):
        while True:
            autosteps = flow.next_autosteps()
            steps = flow.next_steps()

            if not steps:
                log.debug("Flow ended correctly.Nothing left to do.")
                break

            if not autosteps:
                possible_next_steps = ["You are in the flow %s, you can continue with:\n\n" % flow]
                for step in steps:
                    possible_next_steps.append("- " + step.command)  # TODO: put syntax too.
                self._bot.send(flow.requestor, "\n".join(possible_next_steps))
                break

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
