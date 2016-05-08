# coding=utf-8
import re
import logging
from os import path, mkdir
from queue import Empty
from shutil import rmtree

import pytest

from errbot.backends.test import testbot  # noqa

extra_plugin_dir = path.join(path.dirname(path.realpath(__file__)), 'dummy_plugin')


def test_root_help(testbot):
    testbot.assertCommand('!help', 'All commands')


def test_help(testbot):
    testbot.assertCommand('!help Help', '!about')
    testbot.assertCommand('!help beurk', 'That command is not defined.')

    # Ensure that help reports on re_commands.
    testbot.assertCommand('!help foo', 'runs foo')  # Part of Dummy
    testbot.assertCommand('!help re_foo', 'runs re_foo')  # Part of Dummy
    testbot.assertCommand('!help re foo', 'runs re_foo')  # Part of Dummy


def test_about(testbot):
    testbot.assertCommand('!about', 'Errbot version')


def test_uptime(testbot):
    testbot.assertCommand('!uptime', 'I\'ve been up for')


def test_status(testbot):
    testbot.assertCommand('!status', 'Yes I am alive')


def test_status_plugins(testbot):
    testbot.assertCommand('!status plugins', 'A = Activated, D = Deactivated')


def test_status_load(testbot):
    testbot.assertCommand('!status load', 'Load ')


def test_whoami(testbot):
    testbot.assertCommand('!whoami', 'person')
    testbot.assertCommand('!whoami', 'gbin@localhost')


def test_echo(testbot):
    testbot.assertCommand('!echo foo', 'foo')


def test_status_gc(testbot):
    testbot.assertCommand('!status gc', 'GC 0->')


def test_config_cycle(testbot):
    testbot.bot.push_message('!plugin config Webserver')
    m = testbot.bot.pop_message()
    assert 'Default configuration for this plugin (you can copy and paste this directly as a command)' in m
    assert 'Current configuration' not in m

    testbot.assertCommand("!plugin config Webserver {'HOST': 'localhost', 'PORT': 3141, 'SSL':  None}",
                          'Plugin configuration done.')

    testbot.assertCommand('!plugin config Webserver', 'Current configuration')
    testbot.assertCommand('!plugin config Webserver', 'localhost')


def test_apropos(testbot):
    testbot.assertCommand('!apropos about', '!about: Return information about')


def test_logtail(testbot):
    testbot.assertCommand('!log tail', 'DEBUG')


def test_history(testbot):
    testbot.assertCommand('!uptime', 'up')
    testbot.assertCommand('!history', 'uptime')

    orig_sender = testbot.bot.sender
    try:
        # Pretend to be someone else. History should be empty
        testbot.bot.sender = testbot.bot.build_identifier('non_default_person')
        testbot.bot.push_message('!history')
        with pytest.raises(Empty):
            testbot.bot.pop_message(block=False)
        testbot.bot.push_message('!echo should be a separate history')
        testbot.bot.pop_message()
        testbot.assertCommand('!history', 'should be a separate history')
    finally:
        testbot.bot.sender = orig_sender
    # Pretend to be the original person again. History should still contain uptime
    testbot.assertCommand('!history', 'uptime')


def test_plugin_cycle(testbot):

    plugins = [
        'errbotio/err-helloworld',
    ]

    for plugin in plugins:
        testbot.assertCommand(
            '!repos install {0}'.format(plugin),
            'Installing {0}...'.format(plugin)
        ),
        assert 'A new plugin repository has been installed correctly from errbotio/err-helloworld' in \
               testbot.bot.pop_message(timeout=60)
        assert 'Plugins reloaded' in testbot.bot.pop_message()

        testbot.assertCommand('!help hello', 'this command says hello')
        testbot.assertCommand('!hello', 'Hello World !')

        testbot.bot.push_message('!plugin reload HelloWorld')
        assert 'Plugin HelloWorld reloaded.' == testbot.bot.pop_message()

        testbot.bot.push_message('!hello')  # should still respond
        assert 'Hello World !' == testbot.bot.pop_message()

        testbot.bot.push_message('!plugin blacklist HelloWorld')
        assert 'Plugin HelloWorld is now blacklisted' == testbot.bot.pop_message()
        testbot.bot.push_message('!plugin deactivate HelloWorld')
        assert 'HelloWorld is already deactivated.' == testbot.bot.pop_message()

        testbot.bot.push_message('!hello')  # should not respond
        assert 'Command "hello" not found' in testbot.bot.pop_message()

        testbot.bot.push_message('!plugin unblacklist HelloWorld')
        assert 'Plugin HelloWorld removed from blacklist' == testbot.bot.pop_message()
        testbot.bot.push_message('!plugin activate HelloWorld')
        assert 'HelloWorld is already activated.' == testbot.bot.pop_message()

        testbot.bot.push_message('!hello')  # should respond back
        assert 'Hello World !' == testbot.bot.pop_message()

        testbot.bot.push_message('!repos uninstall errbotio/err-helloworld')
        assert 'Repo errbotio/err-helloworld removed.' == testbot.bot.pop_message()

        testbot.bot.push_message('!hello')  # should not respond
        assert 'Command "hello" not found' in testbot.bot.pop_message()


def test_broken_plugin(testbot):
    testbot.assertCommand(
        '!repos install https://github.com/errbotio/err-broken.git',
        'Installing',
        60
    )
    assert 'import borken # fails' in testbot.bot.pop_message()
    assert 'err-broken as it did not load correctly.' in testbot.bot.pop_message()
    assert 'Plugins reloaded.' in testbot.bot.pop_message()


def test_backup(testbot):
    bot = testbot.bot  # used while restoring
    bot.push_message('!repos install https://github.com/errbotio/err-helloworld.git')
    assert 'Installing' in testbot.bot.pop_message()
    assert 'err-helloworld' in testbot.bot.pop_message(timeout=60)
    assert 'reload' in testbot.bot.pop_message()
    bot.push_message('!backup')
    msg = testbot.bot.pop_message()
    assert 'has been written in' in msg
    filename = re.search(r"'([A-Za-z0-9_\./\\-]*)'", msg).group(1)

    # At least the backup should mention the installed plugin
    assert 'errbotio/err-helloworld' in open(filename).read()

    # Now try to clean the bot and restore
    for p in testbot.bot.plugin_manager.get_all_active_plugin_objects():
        p.close_storage()

    testbot.assertCommand('!plugin deactivate HelloWorld', 'Plugin HelloWorld deactivated.')

    plugins_dir = path.join(testbot.bot.bot_config.BOT_DATA_DIR, 'plugins')
    bot.repo_manager['installed_repos'] = {}
    bot.plugin_manager['configs'] = {}
    rmtree(plugins_dir)
    mkdir(plugins_dir)

    # emulates the restore environment
    log = logging.getLogger(__name__)  # noqa
    with open(filename) as f:
        exec(f.read())

    testbot.assertCommand('!plugin activate HelloWorld', 'Plugin HelloWorld activated.')
    testbot.assertCommand('!hello', 'Hello World !')
    testbot.bot.push_message('!repos uninstall errbotio/err-helloworld')


def test_encoding_preservation(testbot):
    testbot.bot.push_message('!echo へようこそ')
    assert 'へようこそ' == testbot.bot.pop_message()


def test_webserver_webhook_test(testbot):
    testbot.bot.push_message("!plugin config Webserver {'HOST': 'localhost', 'PORT': 3141, 'SSL':  None}")
    assert 'Plugin configuration done.' in testbot.bot.pop_message()
    testbot.assertCommand("!webhook test /echo toto", 'Status code : 200')


def test_activate_reload_and_deactivate(testbot):
    for command in ('activate', 'reload', 'deactivate'):
        testbot.bot.push_message("!plugin {}".format(command))
        m = testbot.bot.pop_message()
        assert 'Please tell me which of the following plugins to' in m
        assert 'ChatRoom' in m

        testbot.bot.push_message('!plugin {} nosuchplugin'.format(command))
        m = testbot.bot.pop_message()
        assert 'nosuchplugin isn\'t a valid plugin name. The current plugins are' in m
        assert 'ChatRoom' in m

    testbot.bot.push_message('!plugin reload ChatRoom')
    assert 'Plugin ChatRoom reloaded.' == testbot.bot.pop_message()

    testbot.bot.push_message('!status plugins')
    assert 'A      │ ChatRoom' in testbot.bot.pop_message()

    testbot.bot.push_message('!plugin deactivate ChatRoom')
    assert 'Plugin ChatRoom deactivated.' == testbot.bot.pop_message()

    testbot.bot.push_message("!status plugins")
    assert 'D      │ ChatRoom' in testbot.bot.pop_message()

    testbot.bot.push_message('!plugin deactivate ChatRoom')
    assert 'ChatRoom is already deactivated.' in testbot.bot.pop_message()

    testbot.bot.push_message('!plugin activate ChatRoom')
    assert 'Plugin ChatRoom activated.' in testbot.bot.pop_message()

    testbot.bot.push_message('!status plugins')
    assert 'A      │ ChatRoom' in testbot.bot.pop_message()

    testbot.bot.push_message('!plugin activate ChatRoom')
    assert 'ChatRoom is already activated.' == testbot.bot.pop_message()

    testbot.bot.push_message('!plugin deactivate ChatRoom')
    assert 'Plugin ChatRoom deactivated.' == testbot.bot.pop_message()
    testbot.bot.push_message('!plugin reload ChatRoom')
    assert 'Warning: plugin ChatRoom is currently not activated. Use !plugin activate ChatRoom to activate it.' == \
           testbot.bot.pop_message()
    assert 'Plugin ChatRoom reloaded.' == testbot.bot.pop_message()

    testbot.bot.push_message('!plugin blacklist ChatRoom')
    assert 'Plugin ChatRoom is now blacklisted' == testbot.bot.pop_message()

    testbot.bot.push_message('!status plugins')
    assert 'B,D    │ ChatRoom' in testbot.bot.pop_message()

    # Needed else configuration for this plugin gets saved which screws up
    # other tests
    testbot.bot.push_message('!plugin unblacklist ChatRoom')
    testbot.bot.pop_message()


def test_unblacklist_and_blacklist(testbot):
    testbot.bot.push_message('!plugin unblacklist nosuchplugin')
    m = testbot.bot.pop_message()
    assert "nosuchplugin isn't a valid plugin name. The current plugins are" in m
    assert 'ChatRoom' in m

    testbot.bot.push_message('!plugin blacklist nosuchplugin')
    m = testbot.bot.pop_message()
    assert "nosuchplugin isn't a valid plugin name. The current plugins are" in m
    assert 'ChatRoom' in m

    testbot.bot.push_message('!plugin blacklist ChatRoom')
    assert 'Plugin ChatRoom is now blacklisted' in testbot.bot.pop_message()

    testbot.bot.push_message('!plugin blacklist ChatRoom')
    assert 'Plugin ChatRoom is already blacklisted' == testbot.bot.pop_message()

    testbot.bot.push_message('!status plugins')
    assert 'B,D    │ ChatRoom' in testbot.bot.pop_message()

    testbot.bot.push_message('!plugin unblacklist ChatRoom')
    assert 'Plugin ChatRoom removed from blacklist' == testbot.bot.pop_message()

    testbot.bot.push_message('!plugin unblacklist ChatRoom')
    assert 'Plugin ChatRoom is not blacklisted' == testbot.bot.pop_message()

    testbot.bot.push_message('!status plugins')
    assert 'A      │ ChatRoom' in testbot.bot.pop_message()


def test_optional_prefix(testbot):
    # Let's not leave any side effects
    prefix_optional = testbot.bot.bot_config.BOT_PREFIX_OPTIONAL_ON_CHAT

    testbot.bot.bot_config.BOT_PREFIX_OPTIONAL_ON_CHAT = False
    testbot.assertCommand('!status', 'Yes I am alive')

    testbot.bot.bot_config.BOT_PREFIX_OPTIONAL_ON_CHAT = True
    testbot.assertCommand('!status', 'Yes I am alive')
    testbot.assertCommand('status', 'Yes I am alive')

    # Now reset our state so we don't bork the other tests
    testbot.bot.bot_config.BOT_PREFIX_OPTIONAL_ON_CHAT = prefix_optional


def test_optional_prefix_re_cmd(testbot):
    # Let's not leave any side effects
    prefix_optional = testbot.bot.bot_config.BOT_PREFIX_OPTIONAL_ON_CHAT

    testbot.bot.bot_config.BOT_PREFIX_OPTIONAL_ON_CHAT = False
    testbot.assertCommand('!plz dont match this', 'bar')

    testbot.bot.bot_config.BOT_PREFIX_OPTIONAL_ON_CHAT = True
    testbot.assertCommand('!plz dont match this', 'bar')
    testbot.assertCommand('plz dont match this', 'bar')

    # Now reset our state so we don't bork the other tests
    testbot.bot.bot_config.BOT_PREFIX_OPTIONAL_ON_CHAT = prefix_optional


def test_simple_match(testbot):
    testbot.assertCommand('match this', 'bar')
