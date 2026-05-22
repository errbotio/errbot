from os import path

# This is to test end2end i18n behavior.

extra_plugin_dir = path.join(path.dirname(path.realpath(__file__)), "template_plugin")


def test_templates_1(testbot):
    assert "ok" in testbot.exec_command("!test template1")


def test_templates_2(testbot):
    assert "ok" in testbot.exec_command("!test template2")


def test_templates_3(testbot):
    assert "ok" in testbot.exec_command("!test template3")


def test_templates_4(testbot):
    assert "ok" in testbot.exec_command("!test template4 ok")


def test_templates_5(testbot):
    assert "the following arguments are required: my_var" in testbot.exec_command(
        "!test template4"
    )


def test_template_collision(testbot):
    # Test CollisionA (namespaced)
    testbot.push_message("!test_a")
    response = testbot.pop_message()
    assert "Template from PluginA" in response

    # Test CollisionB (namespaced)
    testbot.push_message("!test_b")
    response = testbot.pop_message()
    assert "Template from PluginB (B)" in response

    # Test manual send_templated (respects namespace)
    testbot.push_message("!test_manual")
    response = testbot.pop_message()
    assert "Template from PluginA" in response
