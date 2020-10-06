import logging

import pytest

from errbot.backends.test import TestPerson
from errbot.flow import Flow, FlowRoot, InvalidState

log = logging.getLogger(__name__)


def test_node():
    root = FlowRoot("test", "This is my flowroot")
    node = root.connect("a", lambda ctx: ctx["toto"] == "titui")

    assert root.predicate_for_node(node)({"toto": "titui"})
    assert not root.predicate_for_node(node)({"toto": "blah"})


def test_flow_predicate():
    root = FlowRoot("test", "This is my flowroot")
    node = root.connect("a", lambda ctx: "toto" in ctx and ctx["toto"] == "titui")
    somebody = TestPerson("me")

    # Non-matching predicate
    flow = Flow(root, somebody, {})
    assert node in flow.next_steps()
    assert node not in flow.next_autosteps()
    with pytest.raises(InvalidState):
        flow.advance(node)

    flow.advance(node, enforce_predicate=False)  # This will bypass the restriction
    assert flow._current_step == node

    # Matching predicate
    flow = Flow(root, somebody, {"toto": "titui"})
    assert node in flow.next_steps()
    assert node in flow.next_autosteps()
    flow.advance(node)
    assert flow._current_step == node


def test_autotrigger():
    root = FlowRoot("test", "This is my flowroot")
    node = root.connect(
        "a", lambda ctx: "toto" in ctx and ctx["toto"] == "titui", auto_trigger=True
    )
    assert node.command in root.auto_triggers
