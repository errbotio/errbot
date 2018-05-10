from os import path

extra_plugin_dir = path.join(path.dirname(path.realpath(__file__)), "mention_plugin")


def test_foreign_mention(testbot):
    assert "Somebody mentioned toto!" in testbot.exec_command("I am telling you something @toto")


def test_testbot_mention(testbot):
    assert "Somebody mentioned me!" in testbot.exec_command("I am telling you something @Err")


def test_multiple_mentions(testbot):
    assert "Somebody mentioned toto,titi!" in testbot.exec_command("I am telling you something @toto and @titi")
