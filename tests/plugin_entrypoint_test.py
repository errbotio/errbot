from errbot.utils import entry_point_plugins


def test_entrypoint_paths():
    plugins = entry_point_plugins("console_scripts")

    match = False
    for plugin in plugins:
        if "errbot/errbot.cli" in plugin:
            match = True
    assert match


def test_entrypoint_paths_empty():
    groups = ["errbot.plugins", "errbot.backend_plugins"]
    for entry_point_group in groups:
        plugins = entry_point_plugins(entry_point_group)
        assert plugins == []
