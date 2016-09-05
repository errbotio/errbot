from os import path
from queue import Empty

import pytest

from errbot.backends.test import testbot

extra_plugin_dir = path.join(path.dirname(path.realpath(__file__)), 'flow_plugin')


def test_list_flows(testbot):
    assert len(testbot.bot.flow_executor.flow_roots) == 3
    testbot.bot.push_message('!flows list')
    result = testbot.pop_message()
    assert 'documentation of W1' in result
    assert 'documentation of W2' in result
    assert 'documentation of W3' in result
    assert 'w1' in result
    assert 'w2' in result
    assert 'w3' in result


def test_no_autotrigger(testbot):
    assert 'a' in testbot.exec_command('!a')
    assert len(testbot.bot.flow_executor.in_flight) == 0


def test_autotrigger(testbot):
    assert 'c' in testbot.exec_command('!c')
    flow_message = testbot.pop_message()
    assert 'You are in the flow w2, you can continue with' in flow_message
    assert '!b' in flow_message
    assert len(testbot.bot.flow_executor.in_flight) == 1
    assert testbot.bot.flow_executor.in_flight[0].name == 'w2'


def test_no_duplicate_autotrigger(testbot):
    assert 'c' in testbot.exec_command('!c')
    flow_message = testbot.pop_message()
    assert 'You are in the flow w2, you can continue with' in flow_message
    assert 'c' in testbot.exec_command('!c')
    assert len(testbot.bot.flow_executor.in_flight) == 1
    assert testbot.bot.flow_executor.in_flight[0].name == 'w2'


def test_secondary_autotrigger(testbot):
    assert 'e' in testbot.exec_command('!e')
    second_message = testbot.pop_message()
    assert 'You are in the flow w2, you can continue with' in second_message
    assert '!d' in second_message
    assert len(testbot.bot.flow_executor.in_flight) == 1
    assert testbot.bot.flow_executor.in_flight[0].name == 'w2'


def test_manual_flow(testbot):
    assert 'Flow w1 started' in testbot.exec_command('!flows start w1')
    flow_message = testbot.pop_message()
    assert 'You are in the flow w1, you can continue with' in flow_message
    assert '!a' in flow_message
    assert 'a' in testbot.exec_command('!a')
    flow_message = testbot.pop_message()
    assert 'You are in the flow w1, you can continue with' in flow_message
    assert '!b' in flow_message
    assert '!c' in flow_message


def test_no_flyby_trigger_flow(testbot):
    testbot.bot.push_message('!flows start w1')
    # One message or the other can arrive first.
    flow_message = testbot.pop_message()
    assert 'Flow w1 started' in flow_message or 'You are in the flow w1' in flow_message
    flow_message = testbot.pop_message()
    assert 'Flow w1 started' in flow_message or 'You are in the flow w1' in flow_message
    assert 'a' in testbot.exec_command('!a')
    flow_message = testbot.pop_message()
    assert 'You are in the flow w1' in flow_message

    assert 'c' in testbot.exec_command('!c')  # c is a trigger for w2 but it should not trigger now.
    flow_message = testbot.pop_message()
    assert 'You are in the flow w1' in flow_message
    assert len(testbot.bot.flow_executor.in_flight) == 1


def test_flow_only(testbot):
    assert 'a' in testbot.exec_command('!a')  # non flow_only should respond.
    testbot.push_message('!d')
    with pytest.raises(Empty):
        testbot.pop_message(timeout=1)


def test_flow_only_help(testbot):
    testbot.push_message('!help')
    msg = testbot.bot.pop_message()
    assert '!a' in msg  # non flow_only should be in help by default
    assert '!d' not in msg  # flow_only should not be in help by default


def test_flows_stop(testbot):
    assert 'c' in testbot.exec_command('!c')
    flow_message = testbot.bot.pop_message()
    assert 'You are in the flow w2' in flow_message
    assert 'w2 stopped' in testbot.exec_command('!flows stop w2')
    assert len(testbot.bot.flow_executor.in_flight) == 0


def test_flows_kill(testbot):
    assert 'c' in testbot.exec_command('!c')
    flow_message = testbot.bot.pop_message()
    assert 'You are in the flow w2' in flow_message
    assert 'w2 killed' in testbot.exec_command('!flows kill gbin@localhost w2')


def test_room_flow(testbot):
    assert 'Flow w3 started' in testbot.exec_command('!flows start w3')
    flow_message = testbot.pop_message()
    assert 'You are in the flow w3, you can continue with' in flow_message
    assert '!a' in flow_message
    assert 'a' in testbot.exec_command('!a')
    flow_message = testbot.pop_message()
    assert 'You are in the flow w3, you can continue with' in flow_message
    assert '!b' in flow_message
