from os import path
import time

CURRENT_FILE_DIR = path.dirname(path.realpath(__file__))
extra_plugin_dir = path.join(CURRENT_FILE_DIR, 'poller_plugin')


def test_delayed_hello(testbot):
    assert 'Hello, world!' in testbot.exec_command('!hello')
    time.sleep(1)
    delayed_msg = 'Hello world! was sent 5 seconds ago'
    assert delayed_msg in testbot.pop_message(timeout=1)
    # Assert that only one message has been enqueued
    assert testbot.bot.outgoing_message_queue.empty()


def test_delayed_hello_loop(testbot):
    assert 'Hello, world!' in testbot.exec_command('!hello_loop')
    time.sleep(1)
    delayed_msg = 'Hello world! was sent 5 seconds ago'
    assert delayed_msg in testbot.pop_message(timeout=1)
    # Assert that only one message has been enqueued
    assert testbot.bot.outgoing_message_queue.empty()
