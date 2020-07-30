import os
import pytest
import tempfile
from configparser import ConfigParser
from pathlib import Path

import errbot.repo_manager
from errbot import plugin_manager
from errbot.plugin_info import PluginInfo
from errbot.plugin_manager import IncompatiblePluginException
from errbot.utils import find_roots, collect_roots

CORE_PLUGINS = plugin_manager.CORE_PLUGINS


def touch(name):
    with open(name, 'a'):
        os.utime(name, None)


assets = Path(__file__).parent / 'assets'


def test_check_dependencies():
    response, deps = errbot.repo_manager.check_dependencies(assets / 'requirements_never_there.txt')
    assert 'You need these dependencies for' in response
    assert 'impossible_requirement' in response
    assert ['impossible_requirement'] == deps


def test_check_dependencies_no_requirements_file():
    response, deps = errbot.repo_manager.check_dependencies(assets / 'requirements_non_existent.txt')
    assert response is None


def test_check_dependencies_requirements_file_all_installed():
    response, deps = errbot.repo_manager.check_dependencies(assets / 'requirements_already_there.txt')
    assert response is None


def test_find_plugin_roots():
    root = tempfile.mkdtemp()
    a = os.path.join(root, 'a')
    b = os.path.join(a, 'b')
    c = os.path.join(root, 'c')
    os.mkdir(a)
    os.mkdir(b)
    os.mkdir(c)
    touch(os.path.join(a, 'toto.plug'))
    touch(os.path.join(b, 'titi.plug'))
    touch(os.path.join(root, 'tutu.plug'))
    roots = find_roots(root)
    assert root in roots
    assert a in roots
    assert b in roots
    assert c not in roots


def test_collect_roots():
    toto = tempfile.mkdtemp()
    touch(os.path.join(toto, 'toto.plug'))
    touch(os.path.join(toto, 'titi.plug'))
    titi = tempfile.mkdtemp()
    touch(os.path.join(titi, 'tata.plug'))
    tutu = tempfile.mkdtemp()
    subtutu = os.path.join(tutu, 'subtutu')
    os.mkdir(subtutu)
    touch(os.path.join(subtutu, 'tutu.plug'))

    assert collect_roots((CORE_PLUGINS, None)) == [CORE_PLUGINS]
    assert collect_roots((CORE_PLUGINS, toto)) == [CORE_PLUGINS, toto]
    assert collect_roots((CORE_PLUGINS, [toto, titi])) == [CORE_PLUGINS, toto, titi]
    assert collect_roots((CORE_PLUGINS, toto, titi, 'nothing')) == [CORE_PLUGINS, toto, titi]
    assert collect_roots((toto, tutu)) == [toto, subtutu]


def test_ignore_dotted_directories():
    root = tempfile.mkdtemp()
    a = os.path.join(root, '.invisible')
    os.mkdir(a)
    touch(os.path.join(a, 'toto.plug'))
    assert collect_roots((CORE_PLUGINS, root)) == [CORE_PLUGINS]


def dummy_config_parser() -> ConfigParser:
    cp = ConfigParser()
    cp.add_section('Core')
    cp.set('Core', 'Name', 'dummy')
    cp.set('Core', 'Module', 'dummy')
    cp.add_section('Errbot')
    return cp


def test_errbot_version_check():
    real_version = plugin_manager.VERSION

    too_high_min_1 = dummy_config_parser()
    too_high_min_1.set('Errbot', 'Min', '1.6.0')

    too_high_min_2 = dummy_config_parser()
    too_high_min_2.set('Errbot', 'Min', '1.6.0')
    too_high_min_2.set('Errbot', 'Max', '2.0.0')

    too_low_max_1 = dummy_config_parser()
    too_low_max_1.set('Errbot', 'Max', '1.0.1-beta')

    too_low_max_2 = dummy_config_parser()
    too_low_max_2.set('Errbot', 'Min', '0.9.0-rc2')
    too_low_max_2.set('Errbot', 'Max', '1.0.1-beta')

    ok1 = dummy_config_parser()  # empty section

    ok2 = dummy_config_parser()
    ok2.set('Errbot', 'Min', '1.4.0')

    ok3 = dummy_config_parser()
    ok3.set('Errbot', 'Max', '1.5.2')

    ok4 = dummy_config_parser()
    ok4.set('Errbot', 'Min', '1.2.1')
    ok4.set('Errbot', 'Max', '1.6.1-rc1')

    try:
        plugin_manager.VERSION = '1.5.2'
        for config in (too_high_min_1,
                       too_high_min_2,
                       too_low_max_1,
                       too_low_max_2):
            pi = PluginInfo.parse(config)
            with pytest.raises(IncompatiblePluginException):
                plugin_manager.check_errbot_version(pi)

        for config in (ok1, ok2, ok3, ok4):
            pi = PluginInfo.parse(config)
            plugin_manager.check_errbot_version(pi)
    finally:
        plugin_manager.VERSION = real_version
