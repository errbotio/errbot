Testing your plugins
====================

Just as Err has tests that validates that it behaves correctly so should your plugin. Err is tested using Python's unittest_ module and because we already provide some utilities for that we highly advise you to use `unittest` too.

We're going to write a simple plugin named `myplugin.py` with a `MyPlugin` class. It's tests will be stored in `test_myplugin.py` in the same directory.

Interacting with the bot
------------------------

Lets go for an example, *myplugin.py*::

    from errbot import BotPlugin, botcmd

    class MyPlugin(BotPlugin):
        @botcmd
        def mycommand(self, message, args):
            return "This is my awesome command"

And *myplugin.plug*:

.. code-block:: ini

    [Core]
    Name = MyPlugin
    Module = myplugin

    [Documentation]
    Description = my plugin


This does absolutely nothing shocking, but how do you test it? We need to interact with the bot somehow, send it `!mycommand` and validate the reply. Fortunatly Err provides some help.

Our test, *test_myplugin.py*::

    import os
    from errbot.backends.test import FullStackTest, pushMessage, popMessage

    class MyPluginTests(FullStackTest):
        def setUp(self):
            me = os.path.dirname(os.path.realpath(os.path.abspath(__file__)))
            # Adding /la/bla to path is needed because of the path mangling
            # FullStackTest does on extra_test_file.
            plugin_dir = os.path.join(me, 'la', 'bla')
            super(MyPluginTests, self).setUp(extra_test_file=plugin_dir)

        def test_command(self):
            pushMessage('!mycommand')
            self.assertIn('This is my awesome command', popMessage())

Lets walk through this line for line. First of all, we import :class:`~errbot.backends.test.FullStackTest`, :func:`~errbot.backends.test.pushMessage` and :func:`~errbot.backends.test.popMessage` from the backends tests, there allow us to spin up a bot for testing purposes and interact with the message queue.

Then we define our own test class subclassing from FullStackTest so we get a bot. We define our own :func:`~errbot.backends.test.FullStackTest.setUp` method because we need to pass the current directory we're executing from to :class:`~errbot.backends.test.FullStackTest` so that it knows to add that directory to the bot's plugin path.

After that we define our first `test_` method which simply sends a command to the bot using :func:`~errbot.backends.test.pushMessage` and then asserts that the response we expect, *"This is my awesome command"* is in the message we receive from the bot which we get by calling :func:`~errbot.backends.test.popMessage`.

Helper methods
--------------

Often enough you'll have methods in your plugins that do things for you that are not decorated with `@botcmd` since the user never calls out to these methods directly.

Such helper methods can be either instance methods, methods that take `self` as the first argument becaus they need access to data stored on the bot or class or static methods, decorated with either `@classmethod` or `@staticmethod`::

    class MyPlugin(BotPlugin):
        @botcmd
        def mycommand(self, message, args):
            return self.mycommand_helper()

        @staticmethod
        def mycommand_helper():
            return "This is my awesome command"

The `mycommand_helper` method does not need any information stored on the bot whatsoever or any other bot state. It can function standalone but it makes sense organisation-wise to have it be a member of the `MyPlugin` class.

Such methods can be tested very easily, without needing a bot::

    import unittest
    import myplugin

    class MyPluginTests(unittest.TestCase):

        def test_mycommand_helper(self):
            expected = "This is my awesome command"
            result = myplugin.MyPlugin.mycommand_helper()
            self.assertEqual(result, expected)

Here we simply import `myplugin` and since it's a `@staticmethod` we can directly access it through `myplugin.MyPlugin.method()`.

Sometimes however a helper method needs information stored on the bot or manipulate some of that so you declare an instance method instead::

    class MyPlugin(BotPlugin):
        @botcmd
        def mycommand(self, message, args):
            return self.mycommand_helper()

        def mycommand_helper(self):
            return "This is my awesome command"

Now what? We can't access the method directly anymore because we need an instance of the bot and the plugin and we can't just send `!mycommand_helper` to the bot, it's not a bot command (and if it were it would be `!mycommand helper` anyway).

What we need now is get access to the instance of our plugin itself. Fortunately for us, there's a method that can help us do just that::

    import os
    from errbot.backends.test import FullStackTest
    from errbot import plugin_manager

    class MyPluginTests(FullStackTest):
        def setUp(self):
            me = os.path.dirname(os.path.realpath(os.path.abspath(__file__)))
            # Adding /la/bla to path is needed because of the path mangling
            # FullStackTest does on extra_test_file.
            plugin_dir = os.path.join(me, 'la', 'bla')
            # Call our parent's setUp() method but pass our directory to
            # extra_test_file so our plugin is loaded.
            super(MyPluginTests, self).setUp(extra_test_file=plugin_dir)

        def test_mycommand_helper(self):
            plugin = plugin_manager.get_plugin_obj_by_name('MyPlugin')
            expected = "This is my awesome command"
            result = plugin.mycommand_helper()
            self.assertEqual(result, expected)

There we go, we first grab out plugin thanks to a helper method on :mod:`~errbot.plugin_manager` and then simply execute the method and compare what we get with what we expect. You can also access `@classmethod` or `@staticmethod` methods this way, you just don't have to.

Pattern
-------

It's a good idea to split up your plugin in two types of methods, those that directly interact with the user and those that do extra stuff you need.

If you do this the `@botcmd` methods should only concern themselves with giving output back to the user and calling different other functions it needs in order to fulfill the user's request.

Try to keep as many helper methods simple, there's nothing wrong with having an extra helper or two to avoid having to nest fifteen if-statements. It becomes more legible, easier to maintain and easier to test.

If you can, try to make your helper methods `@staticmethod` decorated functions, it's easier to test and you don't need a full running bot for those tests.

All together now
----------------

*myplugin.py*::

    from errbot import BotPlugin, botcmd

    class MyPlugin(BotPlugin):
        @botcmd
        def mycommand(self, message, args):
            return self.mycommand_helper()

        @botcmd
        def mycommand_another(self, message, args):
            return self.mycommand_another_helper()

        @staticmethod
        def mycommand_helper();
            return "This is my awesome command"

        def mycommand_another_helper(self);
            return "This is another awesome command"

*myplugin.plug*:

.. code-block:: ini

    [Core]
    Name = MyPlugin
    Module = myplugin

    [Documentation]
    Description = my plugin

*test_myplugin.py*::

    import os
    import unittest
    import myplugin
    from errbot.backends.test import FullStackTest, pushMessage, popMessage
    from errbot import plugin_manager

    class MyPluginBotTests(FullStackTest):
        def setUp(self):
            me = os.path.dirname(os.path.realpath(os.path.abspath(__file__)))
            # Adding /la/bla to path is needed because of the path mangling
            # FullStackTest does on extra_test_file.
            plugin_dir = os.path.join(me, 'la', 'bla')
            super(MyPluginBotTests, self).setUp(extra_test_file=plugin_dir)

        def test_mycommand(self):
            pushMessage('!mycommand')
            self.assertIn('This is my awesome command', popMessage())

        def test_mycommand_another(self):
            pushMessage('!mycommand another')
            self.assertIn('This is another awesome command', popMessage())


    class MyPluginStaticMethodTests(unittest.TestCase):

        def test_mycommand_helper(self):
            expected = "This is my awesome command"
            result = myplugin.MyPlugin.mycommand_helper()
            self.assertEqual(result, expected)


    class MyPluginInstanceMethodTests(FullStackTest):
        def setUp(self):
            me = os.path.dirname(os.path.realpath(os.path.abspath(__file__)))
            # Adding /la/bla to path is needed because of the path mangling
            # FullStackTest does on extra_test_file.
            plugin_dir = os.path.join(me, 'la', 'bla')
            # Call our parent's setUp() method but pass our directory to
            # extra_test_file so our plugin is loaded.
            super(MyPluginInstanceMethodTests, self).setUp(extra_test_file=plugin_dir)

        def test_mycommand_another_helper(self):
            plugin = plugin_manager.get_plugin_obj_by_name('MyPlugin')
            expected = "This is another awesome command"
            result = plugin.mycommand_another_helper()
            self.assertEqual(result, expected)

    if __name__ == '__main__':
            unittest.main()

You can now simply run :command:`python test_myplugin.py` to execute the tests.

PEP-8 and code coverage
-----------------------

If you feel like it you can also add syntax checkers like `pep8` into the mix to validate your code behaves to certain stylistic best practices set out in PEP-8.

First, install pep8: :command:`pip install pep8`

Then, add this to your `test_myplugin.py`::

    import pep8

    class TestCodeFormat(unittest.TestCase):
        """Test suite that validates our code adheres to certain standards."""

        def test_pep8_conformance(self):
            """Test that we conform to PEP8."""
            pep8style = pep8.StyleGuide(quiet=True)
            result = pep8style.check_files(['myplugin.py', 'test_myplugin.py'])
            self.assertEqual(result.total_errors, 0,
                             "Found code style errors (and warnings).")

You also want to know how well your tests cover you code.

To that end, install coverage: :command:`pip install coverage` and then run your tests like this: :command:`coverage run --source=myplugin.py test_myplugin.py`.

You can now have a look at coverage statistics through :command:`coverage report`::

    Name        Stmts   Miss  Cover
    -------------------------------
    myplugin      49      0   100%

It's also possible to generate an HTML report with :command:`coverage html` and opening the resulting `htmlcov/index.html`.

Travis and Coveralls
--------------------

Last but not least, you can run your tests on Travis-CI_ so when you update code or others submit pull requests the tests will automatically run confirming everything still works.

In order to do that you'll need a `.travis.yml` similar to this:

.. code-block:: yaml

    language: python
    python:
      - "3.3"
    install:
      - "pip install -q yapsy==1.10.2-pythons2n3 err==2.0.0 --use-wheel"
      - "pip install -q pep8 coverage coveralls --use-wheel"
    script:
      - coverage run --source=myplugin.py test_myplugin.py
    after_success:
      - coveralls
    notifications:
      email: false

Most of it is self-explanatory, except for perhaps the `after_success`. The author of this plugin uses Coveralls.io_ to keep track of code coverage so after a successful build we call out to coveralls and upload the statistics. It's for this reason that we `pip install [..] coveralls [..]` in the `.travis.yml`.

Also note the that we're force-installing a specific Yapsy_ version. This is needed because Yapsy's choice to append `-python2n3` causes newer versions of pip to consider it a pre-release thus refusing it to install if not explicitly asked to. Unfortunately the previous stable of Yapsy on 1.9.x which pip would pick is not Python 3 compatible.

The `-q` flag causes pip to be a lot more quiet and `--use-wheel` will cause pip to use wheels_ if available, speeding up your builds if you happen to depend on something that builds a C-extension.

Both Travis-CI and Coveralls easily integrate with Github hosted code.

.. _unittest: http://docs.python.org/3.3/library/unittest.html
.. _Coveralls.io: https://coveralls.io
.. _Travis-CI: https://travis-ci.org
.. _Yapsy: http://yapsy.sourceforge.net
.. _wheels: http://www.python.org/dev/peps/pep-0427/
