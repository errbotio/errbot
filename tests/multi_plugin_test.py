from os import path

extra_plugin_dir = path.join(path.dirname(path.realpath(__file__)), 'multi_plugin')

# This tests the decorellation between plugin class names and real names by making 2 instances of the same plugin collide on purpose.

def test_first(testbot):
    assert 'mp1' in testbot.exec_command('!name')

def test_first(testbot):
    assert 'mp21' in testbot.exec_command('!mp2-name')

