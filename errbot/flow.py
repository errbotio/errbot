import logging
from threading import RLock
from typing import Mapping, List, Tuple, Union, Callable, Any, Optional

from multiprocessing.pool import ThreadPool

from errbot import Message
from errbot.backends.base import Identifier, Room, RoomOccupant

log = logging.getLogger(__name__)

Predicate = Callable[[Mapping[str, Any]], bool]

EXECUTOR_THREADS = 5  # the maximum number of simultaneous flows in automatic mode at the same time.


class FlowNode(object):
    """
    This is a step in a Flow/conversation. It is linked to a specific botcmd and also a "predicate".

    The predicate is a function that tells the flow executor if the flow can enter the step without the user
    intervention (automatically). The predicates defaults to False.

    The predicate is a function that takes one parameter, the context of the conversation.
    """

    def __init__(self, command: str = None, hints: bool = True):
        """
        Creates a FlowNone, takes the command to which the Node is linked to.
        :param command: the command this Node is linked to. Can only be None if this Node is a Root.
        :param hints: hints the users for the next steps in chat.
        """
        self.command = command
        self.children = []  # (predicate, node)
        self.hints = hints

    def connect(self, node_or_command: Union['FlowNode', str], predicate: Predicate = lambda _: False,
                hints: bool = True):
        """
        Construct the flow graph by connecting this node to another node or a command.
        The predicate is a function that tells the flow executor if the flow can enter the step without the user
        intervention (automatically).
        :param node_or_command: the node or a string for a command you want to connect this Node to
                               (this node or command will be the follow up of this one)
        :param predicate: function with one parameter, the context, to determine of the flow executor can continue
                           automatically this flow with no user intervention.
        :param hints: hints the user on the next step possible.
        :return: the newly created node if you passed a command or the node you gave it to be easily chainable.
        """
        node_to_connect_to = node_or_command if isinstance(node_or_command, FlowNode) else FlowNode(node_or_command,
                                                                                                    hints=hints)
        self.children.append((predicate, node_to_connect_to))
        return node_to_connect_to

    def predicate_for_node(self, node: 'FlowNode'):
        """
        gets the predicate function for the specified child node.
        :param node: the child node
        :return: the predicate that allows the automatic execution of that node.
        """
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
        :param hints: Hints for the next steps when triggered.
        """
        super().__init__()
        self.name = name
        self.description = description
        self.auto_triggers = set()
        self.room_flow = False

    def connect(self,
                node_or_command: Union['FlowNode', str],
                predicate: Predicate = lambda _: False,
                auto_trigger: bool = False,
                room_flow: bool = False):
        """
        :see: FlowNode except fot auto_trigger
        :param predicate: :see: FlowNode
        :param node_or_command: :see: FlowNode
        :param auto_trigger: Flag this root as autotriggering: it will start a flow if this command is executed
                              in the chat.
        :param room_flow: Bind the flow to the room instead of a single person
        """
        resp = super().connect(node_or_command, predicate)
        if auto_trigger:
            self.auto_triggers.add(node_or_command)
        self.room_flow = room_flow
        return resp

    def __str__(self):
        return self.name


class _FlowEnd(FlowNode):
    def __str__(self):
        return 'END'


#: Flow marker indicating that the flow ends.
FLOW_END = _FlowEnd()


class InvalidState(Exception):
    """
    Raised when the Flow Executor is asked to do something contrary to the contraints it has been given.
    """
    pass


class Flow(object):
    """
    This is a live Flow. It keeps context of the conversation (requestor and context).
    Context is just a python dictionary representing the state of the conversation.
    """

    def __init__(self, root: FlowRoot, requestor: Identifier, initial_context: Mapping[str, Any]):
        """

        :param root: the root of this flow.
        :param requestor: the user requesting this flow.
        :param initial_context: any data we already have that could help executing this flow automatically.
        """
        self._root = root
        self._current_step = self._root
        self.ctx = dict(initial_context)
        self.requestor = requestor

    def next_autosteps(self) -> List[FlowNode]:
        """
        Get the next steps that can be automatically executed according to the set predicates.
        """
        return [node for predicate, node in self._current_step.children if predicate(self.ctx)]

    def next_steps(self) -> List[FlowNode]:
        """
        Get all the possible next steps after this one (predicates statisfied or not).
        """
        return [node for predicate, node in self._current_step.children]

    def advance(self, next_step: FlowNode, enforce_predicate=True):
        """
        Move on along the flow.
        :param next_step: Which node you want to move the flow forward to.
        :param enforce_predicate: Do you want to check if the predicate is verified for this step or not.
                                   Usually, if it is a manual step, the predicate is irrelevant because the user
                                   will give the missing information as parameters to the command.
        """
        if enforce_predicate:
            predicate = self._current_step.predicate_for_node(next_step)
            if predicate is None:
                raise ValueError(f'There is no such children: {next_step}.')

            if not predicate(self.ctx):
                raise InvalidState('It is not possible to advance to this step because its predicate is false.')

        self._current_step = next_step

    @property
    def name(self) -> str:
        """
        Helper property to get the name of the flow.
        """
        return self._root.name

    @property
    def current_step(self) -> FlowNode:
        """
        The current step this Flow is waiting on.
        """
        return self._current_step

    @property
    def root(self) -> FlowRoot:
        """
        The original flowroot of this flow.
        """
        return self._root

    def check_identifier(self, identifier: Identifier):
        is_room = isinstance(self.requestor, Room)
        is_room = is_room and isinstance(identifier, RoomOccupant)
        is_room = is_room and self.requestor == identifier.room
        return is_room or self.requestor == identifier

    def __str__(self):
        return f'{self._root} ({self.requestor}) with params {dict(self.ctx)}'


class BotFlow:
    """
    Defines a Flow plugin ie. a plugin that will define new flows from its methods with the @botflow decorator.
    """

    def __init__(self, bot, name=None):
        super().__init__()
        self._bot = bot
        self.is_activated = False
        self._name = name

    @property
    def name(self) -> str:
        """
        Get the name of this flow as described in its .plug file.

        :return: The flow name.
        """
        return self._name

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
        """
            Helper to get a specific command.
        """
        self._bot.all_commands.get(command_name, None)


class FlowExecutor(object):
    """
    This is a instance that can monitor and execute flow instances.
    """

    def __init__(self, bot):
        self._lock = RLock()
        self.flow_roots = {}
        self.in_flight = []
        self._pool = ThreadPool(EXECUTOR_THREADS)
        self._bot = bot

    def add_flow(self, flow: FlowRoot):
        """
        Register a flow with this executor.
        """
        with self._lock:
            self.flow_roots[flow.name] = flow

    def trigger(self, cmd: str, requestor: Identifier, extra_context=None) -> Optional[Flow]:
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

    def check_inflight_already_running(self, user: Identifier) -> bool:
        """
            Check if user is already running a flow.
        :param user: the user
        """
        with self._lock:
            for flow in self.in_flight:
                if flow.requestor == user:
                    return True
        return False

    def check_inflight_flow_triggered(self, cmd: str, user: Identifier) -> Tuple[Optional[Flow], Optional[FlowNode]]:
        """
        Check if a command from a specific user was expected in one of the running flow.
        :param cmd: the command that has just been executed.
        :param user: the identifier of the person who started this flow
        :returns: The name of the flow it triggered or None if none were matching."""
        log.debug("Test if the command %s is a trigger for an inflight flow ...", cmd)
        # TODO: What if 2 flows wait for the same command ?
        with self._lock:
            for flow in self.in_flight:
                if flow.check_identifier(user):
                    log.debug("Requestor has a flow %s in flight", flow.name)
                    for next_step in flow.next_steps():
                        if next_step.command == cmd:
                            log.debug("Requestor has a flow in flight waiting for this command !")
                            return flow, next_step
        log.debug("None matched.")
        return None, None

    def _check_if_new_flow_is_triggered(self, cmd: str, user: Identifier) -> Tuple[Optional[Flow], Optional[FlowNode]]:
        """
        Trigger workflows that may have command cmd as a auto_trigger..
        This assume cmd has been correctly executed.
        :param cmd: the command that has just been executed.
        :param user: the identifier of the person who started this flow
        :returns: The name of the flow it triggered or None if none were matching.
        """
        log.debug("Test if the command %s is an auto-trigger for any flow ...", cmd)
        with self._lock:
            for name, flow_root in self.flow_roots.items():
                if cmd in flow_root.auto_triggers and not self.check_inflight_already_running(user):
                    log.debug("Flow %s has been auto-triggered by the command %s by user %s", name, cmd, user)
                    return self._create_new_flow(flow_root, user, cmd)
        return None, None

    @staticmethod
    def _create_new_flow(flow_root, requestor: Identifier, initial_command) \
            -> Tuple[Optional[Flow], Optional[FlowNode]]:
        """
        Helper method to create a new FLow.
        """
        empty_context = {}
        flow = Flow(flow_root, requestor, empty_context)
        for possible_next_step in flow.next_steps():
            if possible_next_step.command == initial_command:
                # The predicate is good as we just executed manually the command.
                return flow, possible_next_step
        return None, None

    def start_flow(self, name: str, requestor: Identifier, initial_context: Mapping[str, Any]) -> Flow:
        """
        Starts the execution of a Flow.
        """
        if name not in self.flow_roots:
            raise ValueError(f'Flow {name} doesn\'t exist')
        if self.check_inflight_already_running(requestor):
            raise ValueError(f'User {str(requestor)} is already running a flow.')

        flow_root = self.flow_roots[name]
        identity = requestor
        if isinstance(requestor, RoomOccupant) and flow_root.room_flow:
            identity = requestor.room

        flow = Flow(self.flow_roots[name], identity, initial_context)
        self._enqueue_flow(flow)
        return flow

    def stop_flow(self, name: str, requestor: Identifier) -> Optional[Flow]:
        """
        Stops a specific flow. It is a no op if the flow doesn't exist.
        Returns the stopped flow if found.
        """
        with self._lock:
            for flow in self.in_flight:
                if flow.name == name and flow.check_identifier(requestor):
                    log.debug(f'Removing flow {str(flow)}.')
                    self.in_flight.remove(flow)
                    return flow
        return None

    def _enqueue_flow(self, flow):
        with self._lock:
            if flow not in self.in_flight:
                self.in_flight.append(flow)
        self._pool.apply_async(self.execute, (flow,))

    def execute(self, flow: Flow):
        """
        This is where the flow execution happens from one of the thread of the pool.
        """
        while True:
            autosteps = flow.next_autosteps()
            steps = flow.next_steps()

            if not steps:
                log.debug("Flow ended correctly.Nothing left to do.")
                with self._lock:
                    self.in_flight.remove(flow)
                break

            if not autosteps and flow.current_step.hints:
                possible_next_steps = [f'You are in the flow **{flow.name}**, you can continue with:\n\n']
                for step in steps:
                    cmd = step.command
                    cmd_fnc = self._bot.all_commands[cmd]
                    reg_cmd = cmd_fnc._err_re_command
                    syntax_args = cmd_fnc._err_command_syntax
                    reg_prefixed = cmd_fnc._err_command_prefix_required if reg_cmd else True
                    syntax = self._bot.prefix if reg_prefixed else ''
                    if not reg_cmd:
                        syntax += cmd.replace('_', ' ')
                    if syntax_args:
                        syntax += syntax_args
                    possible_next_steps.append(f'- {syntax}')
                self._bot.send(flow.requestor, '\n'.join(possible_next_steps))
                break

            log.debug('Steps triggered automatically %s.', ', '.join(str(node) for node in autosteps))
            log.debug('All possible next steps: %s.', ', '.join(str(node) for node in steps))

            for autostep in autosteps:
                log.debug("Proceeding automatically with step %s", autostep)
                if autostep == FLOW_END:
                    log.debug('This flow ENDED.')
                    with self._lock:
                        self.in_flight.remove(flow)
                    return
                try:
                    msg = Message(frm=flow.requestor, flow=flow)
                    result = self._bot.commands[autostep.command](msg, None)
                    log.debug('Step result %s: %s', flow.requestor, result)

                except Exception as e:
                    log.exception('%s errored at %s', flow, autostep)
                    self._bot.send(flow.requestor, f'{flow} errored at {autostep} with "{e}"')
                flow.advance(autostep)  # TODO: this is only true for a single step, make it forkable.
        log.debug('Flow execution suspended/ended normally.')
