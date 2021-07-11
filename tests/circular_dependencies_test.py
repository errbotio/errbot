import os

extra_plugin_dir = os.path.join(
    os.path.dirname(os.path.realpath(__file__)), "circular_dependent_plugins"
)
pytest_plugins = ["errbot.backends.test"]


def test_if_all_loaded_by_default(testbot):
    """https://github.com/errbotio/errbot/issues/1397"""
    plug_names = testbot.bot.plugin_manager.get_all_active_plugin_names()
    assert "PluginA" in plug_names
    assert "PluginB" in plug_names
    assert "PluginC" in plug_names
