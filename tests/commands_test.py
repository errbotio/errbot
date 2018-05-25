# coding=utf-8
import os
import re
import logging
from os import path, mkdir
from queue import Empty
from shutil import rmtree
from tempfile import mkdtemp

import pytest
import tarfile

extra_plugin_dir = path.join(path.dirname(path.realpath(__file__)), 'dummy_plugin')


def test_root_help(testbot):
    assert 'All commands' in testbot.exec_command('!help')


def test_help(testbot):
    assert '!about' in testbot.exec_command('!help Help')
    assert 'That command is not defined.' in testbot.exec_command('!help beurk')

    # Ensure that help reports on re_commands.
    assert 'runs foo' in testbot.exec_command('!help foo')  # Part of Dummy
    assert 'runs re_foo' in testbot.exec_command('!help re_foo')  # Part of Dummy
    assert 'runs re_foo' in testbot.exec_command('!help re foo')  # Part of Dummy


def test_about(testbot):
    assert 'Errbot version' in testbot.exec_command('!about')


def test_uptime(testbot):
    assert 'I\'ve been up for' in testbot.exec_command('!uptime')


def test_status(testbot):
    assert 'Yes I am alive' in testbot.exec_command('!status')


def test_status_plugins(testbot):
    assert 'A = Activated, D = Deactivated' in testbot.exec_command('!status plugins')


def test_status_load(testbot):
    assert 'Load ' in testbot.exec_command('!status load')


def test_whoami(testbot):
    assert 'person' in testbot.exec_command('!whoami')
    assert 'gbin@localhost' in testbot.exec_command('!whoami')


def test_echo(testbot):
    assert 'foo' in testbot.exec_command('!echo foo')


def test_status_gc(testbot):
    assert 'GC 0->' in testbot.exec_command('!status gc')


def test_config_cycle(testbot):
    testbot.push_message('!plugin config Webserver')
    m = testbot.pop_message()
    assert 'Default configuration for this plugin (you can copy and paste this directly as a command)' in m
    assert 'Current configuration' not in m

    testbot.assertCommand("!plugin config Webserver {'HOST': 'localhost', 'PORT': 3141, 'SSL':  None}",
                          'Plugin configuration done.')

    assert 'Current configuration' in testbot.exec_command('!plugin config Webserver')
    assert 'localhost' in testbot.exec_command('!plugin config Webserver')


def test_apropos(testbot):
    assert '!about: Return information about' in testbot.exec_command('!apropos about')


def test_logtail(testbot):
    assert 'DEBUG' in testbot.exec_command('!log tail')


def test_history(testbot):
    assert 'up' in testbot.exec_command('!uptime')
    assert 'uptime' in testbot.exec_command('!history')

    orig_sender = testbot.bot.sender
    # Pretend to be someone else. History should be empty
    testbot.bot.sender = testbot.bot.build_identifier('non_default_person')
    testbot.push_message('!history')
    with pytest.raises(Empty):
        testbot.pop_message(timeout=1)
    assert 'should be a separate history' in testbot.exec_command('!echo should be a separate history')
    assert 'should be a separate history' in testbot.exec_command('!history')
    testbot.bot.sender = orig_sender
    # Pretend to be the original person again. History should still contain uptime
    assert 'uptime' in testbot.exec_command('!history')


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
               testbot.pop_message(timeout=60)
        assert 'Plugins reloaded' in testbot.pop_message()

        assert 'this command says hello' in testbot.exec_command('!help hello')
        assert 'Hello World !' in testbot.exec_command('!hello')

        testbot.push_message('!plugin reload HelloWorld')
        assert 'Plugin HelloWorld reloaded.' == testbot.pop_message()

        testbot.push_message('!hello')  # should still respond
        assert 'Hello World !' == testbot.pop_message()

        testbot.push_message('!plugin blacklist HelloWorld')
        assert 'Plugin HelloWorld is now blacklisted.' == testbot.pop_message()
        testbot.push_message('!plugin deactivate HelloWorld')
        assert 'HelloWorld is already deactivated.' == testbot.pop_message()

        testbot.push_message('!hello')  # should not respond
        assert 'Command "hello" not found' in testbot.pop_message()

        testbot.push_message('!plugin unblacklist HelloWorld')
        assert 'Plugin HelloWorld removed from blacklist.' == testbot.pop_message()
        testbot.push_message('!plugin activate HelloWorld')
        assert 'HelloWorld is already activated.' == testbot.pop_message()

        testbot.push_message('!hello')  # should respond back
        assert 'Hello World !' == testbot.pop_message()

        testbot.push_message('!repos uninstall errbotio/err-helloworld')
        assert 'Repo errbotio/err-helloworld removed.' == testbot.pop_message()

        testbot.push_message('!hello')  # should not respond
        assert 'Command "hello" not found' in testbot.pop_message()


def test_broken_plugin(testbot):

    borken_plugin_dir = path.join(path.dirname(path.realpath(__file__)), 'borken_plugin')
    try:
        tempd = mkdtemp()
        tgz = os.path.join(tempd, "borken.tar.gz")
        with tarfile.open(tgz, "w:gz") as tar:
            tar.add(borken_plugin_dir, arcname='borken')
        assert 'Installing' in testbot.exec_command('!repos install file://' + tgz, timeout=120)
        assert 'import borken  # fails' in testbot.pop_message()
        assert 'as it did not load correctly.' in testbot.pop_message()
        assert 'Plugins reloaded.' in testbot.pop_message()
    finally:
        rmtree(tempd)


def test_backup(testbot):
    bot = testbot.bot  # used while restoring
    bot.push_message('!repos install https://github.com/errbotio/err-helloworld.git')
    assert 'Installing' in testbot.pop_message()
    assert 'err-helloworld' in testbot.pop_message(timeout=60)
    assert 'reload' in testbot.pop_message()
    bot.push_message('!backup')
    msg = testbot.pop_message()
    assert 'has been written in' in msg
    filename = re.search(r'"(.*)"', msg).group(1)

    # At least the backup should mention the installed plugin
    assert 'errbotio/err-helloworld' in open(filename).read()

    # Now try to clean the bot and restore
    for p in testbot.bot.plugin_manager.get_all_active_plugin_objects():
        p.close_storage()

    assert 'Plugin HelloWorld deactivated.' in testbot.exec_command('!plugin deactivate HelloWorld')

    plugins_dir = path.join(testbot.bot_config.BOT_DATA_DIR, 'plugins')
    bot.repo_manager['installed_repos'] = {}
    bot.plugin_manager['configs'] = {}
    rmtree(plugins_dir)
    mkdir(plugins_dir)

    from errbot.bootstrap import restore_bot_from_backup
    log = logging.getLogger(__name__)  # noqa
    restore_bot_from_backup(filename, bot=bot, log=log)

    assert 'Plugin HelloWorld activated.' in testbot.exec_command('!plugin activate HelloWorld')
    assert 'Hello World !' in testbot.exec_command('!hello')
    testbot.push_message('!repos uninstall errbotio/err-helloworld')


def test_encoding_preservation(testbot):
    testbot.push_message('!echo へようこそ')
    assert 'へようこそ' == testbot.pop_message()


def test_webserver_webhook_test(testbot):
    testbot.push_message("!plugin config Webserver {'HOST': 'localhost', 'PORT': 3141, 'SSL':  None}")
    assert 'Plugin configuration done.' in testbot.pop_message()
    testbot.assertCommand("!webhook test /echo toto", 'Status code : 200')


def test_activate_reload_and_deactivate(testbot):
    for command in ('activate', 'reload', 'deactivate'):
        testbot.push_message("!plugin {}".format(command))
        m = testbot.pop_message()
        assert 'Please tell me which of the following plugins to' in m
        assert 'ChatRoom' in m

        testbot.push_message(f'!plugin {command} nosuchplugin')
        m = testbot.pop_message()
        assert "nosuchplugin isn't a valid plugin name. The current plugins are" in m
        assert 'ChatRoom' in m

    testbot.push_message('!plugin reload ChatRoom')
    assert 'Plugin ChatRoom reloaded.' == testbot.pop_message()

    testbot.push_message('!status plugins')
    assert 'A      │ ChatRoom' in testbot.pop_message()

    testbot.push_message('!plugin deactivate ChatRoom')
    assert 'Plugin ChatRoom deactivated.' == testbot.pop_message()

    testbot.push_message("!status plugins")
    assert 'D      │ ChatRoom' in testbot.pop_message()

    testbot.push_message('!plugin deactivate ChatRoom')
    assert 'ChatRoom is already deactivated.' in testbot.pop_message()

    testbot.push_message('!plugin activate ChatRoom')
    assert 'Plugin ChatRoom activated.' in testbot.pop_message()

    testbot.push_message('!status plugins')
    assert 'A      │ ChatRoom' in testbot.pop_message()

    testbot.push_message('!plugin activate ChatRoom')
    assert 'ChatRoom is already activated.' == testbot.pop_message()

    testbot.push_message('!plugin deactivate ChatRoom')
    assert 'Plugin ChatRoom deactivated.' == testbot.pop_message()
    testbot.push_message('!plugin reload ChatRoom')
    assert 'Warning: plugin ChatRoom is currently not activated. Use !plugin activate ChatRoom to activate it.' == \
           testbot.pop_message()
    assert 'Plugin ChatRoom reloaded.' == testbot.pop_message()

    testbot.push_message('!plugin blacklist ChatRoom')
    assert 'Plugin ChatRoom is now blacklisted.' == testbot.pop_message()

    testbot.push_message('!status plugins')
    assert 'B,D    │ ChatRoom' in testbot.pop_message()

    # Needed else configuration for this plugin gets saved which screws up
    # other tests
    testbot.push_message('!plugin unblacklist ChatRoom')
    testbot.pop_message()


def test_unblacklist_and_blacklist(testbot):
    testbot.push_message('!plugin unblacklist nosuchplugin')
    m = testbot.pop_message()
    assert "nosuchplugin isn't a valid plugin name. The current plugins are" in m
    assert 'ChatRoom' in m

    testbot.push_message('!plugin blacklist nosuchplugin')
    m = testbot.pop_message()
    assert "nosuchplugin isn't a valid plugin name. The current plugins are" in m
    assert 'ChatRoom' in m

    testbot.push_message('!plugin blacklist ChatRoom')
    assert 'Plugin ChatRoom is now blacklisted' in testbot.pop_message()

    testbot.push_message('!plugin blacklist ChatRoom')
    assert 'Plugin ChatRoom is already blacklisted.' == testbot.pop_message()

    testbot.push_message('!status plugins')
    assert 'B,D    │ ChatRoom' in testbot.pop_message()

    testbot.push_message('!plugin unblacklist ChatRoom')
    assert 'Plugin ChatRoom removed from blacklist.' == testbot.pop_message()

    testbot.push_message('!plugin unblacklist ChatRoom')
    assert 'Plugin ChatRoom is not blacklisted.' == testbot.pop_message()

    testbot.push_message('!status plugins')
    assert 'A      │ ChatRoom' in testbot.pop_message()


def test_optional_prefix(testbot):
    testbot.bot_config.BOT_PREFIX_OPTIONAL_ON_CHAT = False
    assert 'Yes I am alive' in testbot.exec_command('!status')

    testbot.bot_config.BOT_PREFIX_OPTIONAL_ON_CHAT = True
    assert 'Yes I am alive' in testbot.exec_command('!status')
    assert 'Yes I am alive' in testbot.exec_command('status')


def test_optional_prefix_re_cmd(testbot):
    testbot.bot_config.BOT_PREFIX_OPTIONAL_ON_CHAT = False
    assert 'bar' in testbot.exec_command('!plz dont match this')

    testbot.bot_config.BOT_PREFIX_OPTIONAL_ON_CHAT = True
    assert 'bar' in testbot.exec_command('!plz dont match this')
    assert 'bar' in testbot.exec_command('plz dont match this')


def test_simple_match(testbot):
    assert 'bar' in testbot.exec_command('match this')


def test_no_suggest_on_re_commands(testbot):
    testbot.push_message('!re_ba')
    # Don't suggest a regexp command.
    assert '!re bar' not in testbot.pop_message()


def test_callback_no_command(testbot):
    extra_plugin_dir = os.path.join(
        os.path.dirname(os.path.realpath(__file__)),
        'commandnotfound_plugin'
    )

    cmd = '!this_is_not_a_real_command_at_all'
    expected_str = "Command fell through: {}".format(cmd)

    testbot.exec_command('!plugin deactivate CommandNotFoundFilter')
    testbot.bot.plugin_manager.update_plugin_places([], extra_plugin_dir)
    testbot.exec_command('!plugin activate TestCommandNotFoundFilter')
    assert expected_str == testbot.exec_command(cmd)


def test_subcommands(testbot):
    # test single subcommand (method is run_subcommands())
    cmd = '!run subcommands with these args'
    cmd_underscore = '!run_subcommands with these args'
    expected_args = 'with these args'
    assert expected_args == testbot.exec_command(cmd)
    assert expected_args == testbot.exec_command(cmd_underscore)

    # test multiple subcmomands (method is run_lots_of_subcommands())
    cmd = '!run lots of subcommands with these args'
    cmd_underscore = '!run_lots_of_subcommands with these args'
    assert expected_args == testbot.exec_command(cmd)
    assert expected_args == testbot.exec_command(cmd_underscore)


def test_command_not_found_with_space_in_bot_prefix(testbot):
    testbot.bot_config.BOT_PREFIX = '! '
    assert 'Command "blah" not found.' in testbot.exec_command('! blah')
    assert 'Command "blah" / "blah toto" not found.' in testbot.exec_command('! blah toto')
