import logging
import unittest

from errbot.backends.test import TestPerson
from errbot.flow import Flow, FlowRoot, InvalidState

log = logging.getLogger(__name__)


class FlowTest(unittest.TestCase):
    def test_node(self):
        root = FlowRoot("test", "This is my flowroot")
        node = root.connect("a", lambda ctx: ctx['toto'] == 'titui')

        self.assertTrue(root.predicate_for_node(node)({'toto': 'titui'}))
        self.assertFalse(root.predicate_for_node(node)({'toto': 'blah'}))

    def test_flow_predicate(self):
        root = FlowRoot("test", "This is my flowroot")
        node = root.connect("a", lambda ctx: 'toto' in ctx and ctx['toto'] == 'titui')
        somebody = TestPerson('me')

        # Non-matching predicate
        flow = Flow(root, somebody, {})
        self.assertIn(node, flow.next_steps())
        self.assertNotIn(node, flow.next_autosteps())
        self.assertRaises(InvalidState, flow.advance, node)
        flow.advance(node, enforce_predicate=False)  # This will bypass the restriction
        self.assertEqual(flow._current_step, node)

        # Matching predicate
        flow = Flow(root, somebody, {'toto': 'titui'})
        self.assertIn(node, flow.next_steps())
        self.assertIn(node, flow.next_autosteps())
        flow.advance(node)
        self.assertEqual(flow._current_step, node)

    def test_autotrigger(self):
        root = FlowRoot("test", "This is my flowroot")
        node = root.connect("a", lambda ctx: 'toto' in ctx and ctx['toto'] == 'titui', auto_trigger=True)
        self.assertIn(node.command, root.auto_triggers)
