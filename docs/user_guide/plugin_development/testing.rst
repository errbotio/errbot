Testing your plugins
====================

Just as Err has tests that validates that it behaves correctly so should your plugin. Err is tested using Python's py.test_ module and because we already provide some utilities for that we highly advise you to use `py.test` too.

We're going to write a simple plugin named `myplugin.py` with a `MyPlugin` class. It's tests will be stored in `test_myplugin.py` in the same directory.

Interacting with the bot
------------------------

Lets go for an example, *myplugin.py*:

.. code-block:: python

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

Our test, *test_myplugin.py*:

.. code-block:: python

    import os
    from errbot.backends.test import testbot, push_message, pop_message


    class TestMyPlugin(object):
        extra_plugin_dir = '.'

        def test_command(self, testbot):
            push_message('!mycommand')
            assert 'This is my awesome command' in pop_message()

Lets walk through this line for line. First of all, we import :class:`~errbot.backends.test.testbot`, :func:`~errbot.backends.test.push_message` and :func:`~errbot.backends.test.pop_message` from the backends tests, there allow us to spin up a bot for testing purposes and interact with the message queue.

Then we define our own test class and inside of it we set `extra_plugin_dir` to `.`, the current directory so that the test bot will pick up on your plugin.

After that we define our first `test_` method which simply sends a command to the bot using :func:`~errbot.backends.test.push_message` and then asserts that the response we expect, *"This is my awesome command"* is in the message we receive from the bot which we get by calling :func:`~errbot.backends.test.pop_message`.

Helper methods
--------------

Often enough you'll have methods in your plugins that do things for you that are not decorated with `@botcmd` since the user never calls out to these methods directly.

Such helper methods can be either instance methods, methods that take `self` as the first argument because they need access to data stored on the bot or class or static methods, decorated with either `@classmethod` or `@staticmethod`:

.. code-block:: python

    class MyPlugin(BotPlugin):
        @botcmd
        def mycommand(self, message, args):
            return self.mycommand_helper()

        @staticmethod
        def mycommand_helper():
            return "This is my awesome command"

The `mycommand_helper` method does not need any information stored on the bot whatsoever or any other bot state. It can function standalone but it makes sense organisation-wise to have it be a member of the `MyPlugin` class.

Such methods can be tested very easily, without needing a bot:

.. code-block:: python

    import myplugin

    class TestMyPlugin(object):

        def test_mycommand_helper(self):
            expected = "This is my awesome command"
            result = myplugin.MyPlugin.mycommand_helper()
            assert result == expected

Here we simply import `myplugin` and since it's a `@staticmethod` we can directly access it through `myplugin.MyPlugin.method()`.

Sometimes however a helper method needs information stored on the bot or manipulate some of that so you declare an instance method instead:

.. code-block:: python

    class MyPlugin(BotPlugin):
        @botcmd
        def mycommand(self, message, args):
            return self.mycommand_helper()

        def mycommand_helper(self):
            return "This is my awesome command"

Now what? We can't access the method directly anymore because we need an instance of the bot and the plugin and we can't just send `!mycommand_helper` to the bot, it's not a bot command (and if it were it would be `!mycommand helper` anyway).

What we need now is get access to the instance of our plugin itself. Fortunately for us, there's a method that can help us do just that:

.. code-block:: python

    import os
    from errbot.backends.test import testbot
    from errbot import plugin_manager

    class TestMyPlugin(object)
        extra_plugin_dir = '.'

        def test_mycommand_helper(self, testbot):
            plugin = plugin_manager.get_plugin_obj_by_name('MyPlugin')
            expected = "This is my awesome command"
            result = plugin.mycommand_helper()
            assert result == expected

There we go, we first grab out plugin thanks to a helper method on :mod:`~errbot.plugin_manager` and then simply execute the method and compare what we get with what we expect. You can also access `@classmethod` or `@staticmethod` methods this way, you just don't have to.

Pattern
-------

It's a good idea to split up your plugin in two types of methods, those that directly interact with the user and those that do extra stuff you need.

If you do this the `@botcmd` methods should only concern themselves with giving output back to the user and calling different other functions it needs in order to fulfill the user's request.

Try to keep as many helper methods simple, there's nothing wrong with having an extra helper or two to avoid having to nest fifteen if-statements. It becomes more legible, easier to maintain and easier to test.

If you can, try to make your helper methods `@staticmethod` decorated functions, it's easier to test and you don't need a full running bot for those tests.

All together now
----------------

*myplugin.py*:

.. code-block:: python

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

*test_myplugin.py*:

.. code-block:: python

    import os
    import unittest
    import myplugin
    from errbot.backends.test import testbot, push_message, pop_message
    from errbot import plugin_manager

    class TestMyPluginBot(object):
        extra_plugin_dir = '.'

        def test_mycommand(self, testbot):
            push_message('!mycommand')
            assert 'This is my awesome command' in pop_message()

        def test_mycommand_another(self, testbot):
            push_message('!mycommand another')
            assert 'This is another awesome command' in pop_message()


    class TestMyPluginStaticMethods(object):

        def test_mycommand_helper(self):
            expected = "This is my awesome command"
            result = myplugin.MyPlugin.mycommand_helper()
            assert result == expected


    class TestMyPluginInstanceMethods(object):
        extra_plugin_dir = '.'

        def test_mycommand_another_helper(self):
            plugin = plugin_manager.get_plugin_obj_by_name('MyPlugin')
            expected = "This is another awesome command"
            result = plugin.mycommand_another_helper()
            assert result == expected

You can now simply run :command:`py.test` to execute the tests.

PEP-8 and code coverage
-----------------------

If you feel like it you can also add syntax checkers like `pep8` into the mix to validate your code behaves to certain stylistic best practices set out in PEP-8.

First, install the pep8 for py.test_: :command:`pip instal pytest-pep8`.

Then, simply add `--pep8` to the test invocation command: `py.test --pep8`.

You also want to know how well your tests cover you code.

To that end, install coverage: :command:`pip install coverage` and then run your tests like this: :command:`coverage run --source myplugin -m py.test --pep8`.

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
      - 2.7
      - 3.3
      - 3.4
    install:
      - pip instal -q err pytest pytest-pep8 --use-wheel
      - pip install -q coverage coveralls --use-wheel
    script:
      - coverage run --source myplugin -m py.test --pep8
    after_success:
      - coveralls
    notifications:
      email: false

Most of it is self-explanatory, except for perhaps the `after_success`. The author of this plugin uses Coveralls.io_ to keep track of code coverage so after a successful build we call out to coveralls and upload the statistics. It's for this reason that we `pip install [..] coveralls [..]` in the `.travis.yml`.

The `-q` flag causes pip to be a lot more quiet and `--use-wheel` will cause pip to use wheels_ if available, speeding up your builds if you happen to depend on something that builds a C-extension.

Both Travis-CI and Coveralls easily integrate with Github hosted code.

.. _py.test: http://pytest.org
.. _Coveralls.io: https://coveralls.io
.. _Travis-CI: https://travis-ci.org
.. _Yapsy: http://yapsy.sourceforge.net
.. _wheels: http://www.python.org/dev/peps/pep-0427/
