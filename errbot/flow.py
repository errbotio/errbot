from collections import MutableMapping
from typing import Mapping, Union

from threadpool import ThreadPool, WorkRequest
from yapsy.IPlugin import IPlugin

from errbot import Message
from errbot.backends.base import Identifier


class FlowContext(MutableMapping):
    def __init__(self):
        self.ctx = {}

    def __getitem__(self, key):
        return self.ctx.__getitem__(key)

    def __iter__(self):
        return self.ctx.__iter__()

    def __len__(self):
        return self.ctx.__len__()

    def __setitem__(self, key, value):
        return self.ctx.__setitem__(key, value)

    def __delitem__(self, key):
        return self.ctx.__delitem__(key)


class FlowMessage(Message, FlowContext):
    def __init__(self, frm: Identifier=None):
        super().__init__(frm=frm)


class Node(object):
    def __init__(self, command=None):  # None = start node
        self.command = command
        self.children = []  # (predicate, node)

    def connect(self, node_or_command, predicate):
        node_to_connect_to = node_or_command if isinstance(node_or_command, Node) else Node(node_or_command)
        self.children.append((predicate, node_to_connect_to))
        return node_to_connect_to

    def predicate_for_node(self, node):
        for predicate, possible_node in self.children:
            if node == possible_node:
                return predicate
        return None

    def __str__(self):
        return self.command


class Flow(Node):
    def __init__(self, name, error_predicate, success_predicate, description):
        super().__init__()
        self.name = name
        self.error_predicate = error_predicate
        self.success_predicate = success_predicate
        self.description = description
    def __str__(self):
        return self.name


class InvalidState(Exception):
    pass


class FlowInstance(object):
    def __init__(self, root: Flow, initial_context):
        self._root = root
        self._current_step = self._root
        self._context = initial_context

    def execute(self):
        return self._current_step.command(self.context, None)

    def next_possible_steps(self):
        return [node for predicate, node in self._current_step.children if predicate(self._context)]

    def advance(self, next_step: Node):
        predicate = self._current_step.predicate_for_node(next_step)
        if predicate is None:
            raise ValueError("There is no such children: %s" % next_step)

        if not predicate(self._context):
            raise InvalidState("It is not possible to advance to this step because its predicate is false")

        self._current_step = next_step
        # TODO: error / success predicates

class BotFlow(IPlugin):
    def __init__(self, bot):
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

    def get_command(self, command_name:str):
        self._bot.commands.get(command_name, None)


class FlowExecutor(object):
    """
    This is a instance that can monitor and execute flow instances.
    """
    def __init__(self):
        self.flows = {}
        self.in_flight = []
        self._pool = ThreadPool(5)

    def add_flow(self, flow: Flow):
        self.flows[flow.name] = flow

    def start_flow(self, name, initial_context: FlowMessage):
        if name not in self.flows:
            raise ValueError("Flow %s doesn't exist" % name)
        flow_instance = FlowInstance(self.flows[name], initial_context)
        self.in_flight.append(FlowInstance, flow_instance)



