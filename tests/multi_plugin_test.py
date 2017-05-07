from os import path

extra_plugin_dir = path.join(path.dirname(path.realpath(__file__)), 'multi_plugin')

# This tests the decorellation between plugin class names and real names by making 2 instances of the same plugin collide on purpose.

def test_first(testbot):
    assert 'Multi1' == testbot.exec_command('!myname')

def test_first(testbot):
    assert 'Multi2' == testbot.exec_command('!multi2-myname')

