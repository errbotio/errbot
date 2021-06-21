import os
import pathlib
import mock
import pytest

extra_plugin_dir = os.path.join(
    os.path.dirname(os.path.realpath(__file__)), "cascade_dependent_plugins"
)

orig_path_glob = pathlib.Path.glob


def reordered_plugin_files(self, pattern):
    if self.name == 'cascade_dependent_plugins':
        yield pathlib.Path(extra_plugin_dir + '/parent2.plug')
        yield pathlib.Path(extra_plugin_dir + '/child1.plug')
        yield pathlib.Path(extra_plugin_dir + '/child2.plug')
        yield pathlib.Path(extra_plugin_dir + '/parent1.plug')
        return
    yield from orig_path_glob(self, pattern)


@pytest.fixture
def mock_before_bot_load():
    patcher = mock.patch.object(pathlib.Path, 'glob', reordered_plugin_files)
    patcher.start()
    yield
    patcher.stop()


def test_dependency_commands(mock_before_bot_load, testbot):
    assert "Hello from Child1" in testbot.exec_command("!parent1 to child1")
    assert "Hello from Child2" in testbot.exec_command("!parent1 to child2")
    assert "Hello from Parent1" in testbot.exec_command("!parent2 to parent1")
