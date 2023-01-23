from errbot.utils import entry_point_plugins


def test_entrypoint_paths():
    plugins = entry_point_plugins("console_scripts")

    matches = []
    for plugin in plugins:
        if "errbot" in plugin:
            break
    else:
        assert False

    assert True
