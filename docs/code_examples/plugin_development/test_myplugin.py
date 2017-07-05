import myplugin

pytest_plugins = ["errbot.backends.test"]
extra_plugin_dir = '.'

def test_mycommand(testbot):
    testbot.push_message('!mycommand')
    assert 'This is my awesome command' in testbot.pop_message()

def test_mycommand_another(testbot):
    testbot.push_message('!mycommand another')
    assert 'This is another awesome command' in testbot.pop_message()

def test_mycommand_helper():
    expected = "This is my awesome command"
    result = myplugin.MyPlugin.mycommand_helper()
    assert result == expected

def test_mycommand_another_helper():
    plugin = testbot._bot.plugin_manager.get_plugin_obj_by_name('MyPlugin')
    expected = "This is another awesome command"
    result = plugin.mycommand_another_helper()
    assert result == expected
