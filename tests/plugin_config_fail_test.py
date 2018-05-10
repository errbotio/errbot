from os import path

extra_plugin_dir = path.join(path.dirname(path.realpath(__file__)), "fail_config_plugin")


def test_failed_config(testbot):
    assert "Incorrect plugin configuration: Message explaining why it failed." in testbot.exec_command(
        "!plugin config Failp {}"
    )
