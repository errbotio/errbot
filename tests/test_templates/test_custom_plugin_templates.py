from os import path

pytest_plugins = 'errbot.backends.test',


extra_config = {'TEMPLATES_EXTRA_DIR': path.join(path.dirname(path.realpath(__file__)), 'templates')}
extra_plugin_dir = path.join(path.dirname(path.realpath(__file__)), '..', 'template_plugin')


def test_overridden_send_templated(testbot):
    assert 'overridden: ok' in testbot.exec_command('!test template1')


def test_overridden_send_templated_default_path(testbot):
    testbot.setup(extra_config={})  # remove explicit extra_config for default 'templates' in bot dir
    assert 'ok' in testbot.exec_command('!test template1')
