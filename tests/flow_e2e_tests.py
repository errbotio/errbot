from os import path
from queue import Empty

from errbot.backends.test import FullStackTest


class TestCommands(FullStackTest):
    def setUp(self, *args, **kwargs):
        kwargs['extra_plugin_dir'] = path.join(path.dirname(path.realpath(__file__)), 'flow_plugin')
        super().setUp(*args, **kwargs)

    def test_list_flows(self):
        self.assertEqual(len(self.bot.flow_executor.flow_roots), 2)
        self.bot.push_message('!flows list')
        result = self.bot.pop_message()
        self.assertIn('documentation of W1', result)
        self.assertIn('documentation of W2', result)
        self.assertIn('w1', result)
        self.assertIn('w2', result)

    def test_no_autotrigger(self):
        self.assertCommand('!a', 'a')
        self.assertEqual(len(self.bot.flow_executor.in_flight), 0)

    def test_autotrigger(self):
        self.assertCommand('!c', 'c')
        flow_message = self.bot.pop_message()
        self.assertIn('You are in the flow w2, you can continue with', flow_message)
        self.assertIn('!b', flow_message)
        self.assertEqual(len(self.bot.flow_executor.in_flight), 1)
        self.assertEqual(self.bot.flow_executor.in_flight[0].name, 'w2')

    def test_secondary_autotrigger(self):
        self.assertCommand('!e', 'e')
        second_message = self.bot.pop_message()
        self.assertIn('You are in the flow w2, you can continue with', second_message)
        self.assertIn('!d', second_message)
        self.assertEqual(len(self.bot.flow_executor.in_flight), 1)
        self.assertEqual(self.bot.flow_executor.in_flight[0].name, 'w2')

    def test_manual_flow(self):
        self.assertCommand('!flows start w1', 'Flow w1 started')
        flow_message = self.bot.pop_message()
        self.assertIn('You are in the flow w1, you can continue with', flow_message)
        self.assertIn('!a', flow_message)
        self.assertCommand('!a', 'a')
        flow_message = self.bot.pop_message()
        self.assertIn('You are in the flow w1, you can continue with', flow_message)
        self.assertIn('!b', flow_message)
        self.assertIn('!c', flow_message)

    def test_no_flyby_trigger_flow(self):
        self.assertCommand('!flows start w1', 'Flow w1 started')
        flow_message = self.bot.pop_message()
        self.assertIn('You are in the flow w1', flow_message)
        self.assertCommand('!a', 'a')
        flow_message = self.bot.pop_message()
        self.assertIn('You are in the flow w1', flow_message)

        self.assertCommand('!c', 'c')  # c is a trigger for w2 but it should not trigger now.
        flow_message = self.bot.pop_message()
        self.assertIn('You are in the flow w1', flow_message)
        self.assertEqual(len(self.bot.flow_executor.in_flight), 1)

    def test_flow_only(self):
        self.assertCommand('!a', 'a')  # non flow_only should respond.
        self.bot.push_message('!d')
        self.assertRaises(Empty, self.bot.pop_message, timeout=1)

    def test_flow_only_help(self):
        self.bot.push_message('!help')
        msg = self.bot.pop_message()
        self.assertIn('!a', msg)  # non flow_only should be in help by default
        self.assertNotIn('!d', msg)  # flow_only should not be in help by default
