Testing your plugins with unittest
==================================

This guide explains how to test your Errbot plugins using the built-in testing framework. Errbot provides a powerful testing backend called ``FullStackTest`` that allows you to write unit tests for your plugins in a familiar unittest style.

Basic Test Setup
--------------

To test your plugin, create a test file (e.g., `test_myplugin.py`) in your plugin's directory. Here's a basic example:

.. code-block:: python

    import unittest
    from pathlib import Path

    from errbot.backends.test import FullStackTest

    path = str(Path(__file__).resolve().parent)
    extra_plugin_dir = path


    class TestMyPlugin(FullStackTest):
        def setUp(self):
            super().setUp(extra_plugin_dir=extra_plugin_dir)

        def test_my_command(self):
            # Simulate a user sending a command
            self.push_message('!hello')
            self.assertIn('Hello!', self.pop_message())

Running Tests
------------

You can run your tests using Python's unittest framework:

.. code-block:: bash

    python -m unittest test_myplugin.py

Test Methods
-----------

FullStackTest provides several methods to help test your plugin's behavior:

1. **Message Handling**:
   - ``push_message(command)``: Simulate a user sending a command
   - ``pop_message(timeout=5, block=True)``: Get the bot's response
   - ``assertInCommand(command, response, timeout=5)``: Assert a command returns expected output
   - ``assertCommandFound(command, timeout=5)``: Assert a command exists

2. **Room Operations**:
   - ``push_presence(presence)``: Simulate presence changes
   - Test room joining/leaving
   - Test room topic changes

3. **Plugin Management**:
   - ``inject_mocks(plugin_name, mock_dict)``: Inject mock objects into a plugin
   - Test plugin configuration
   - Test plugin dependencies

Example Test Cases
----------------

Here are some example test cases showing different testing scenarios:

1. **Basic Command Testing**:

   .. code-block:: python

       def test_basic_command(self):
           self.push_message('!echo test')
           self.assertIn('test', self.pop_message())

2. **Command with Arguments**:

   .. code-block:: python

       def test_command_with_args(self):
           self.push_message('!repeat test 3')
           response = self.pop_message()
           self.assertIn('testtesttest', response)

3. **Error Handling**:

   .. code-block:: python

       def test_error_handling(self):
           self.push_message('!nonexistent')
           response = self.pop_message()
           self.assertIn('Command not found', response)

4. **Mocking Dependencies**:

   .. code-block:: python

       def test_with_mocks(self):
           # Create mock objects
           mock_dict = {
               'external_api': MockExternalAPI()
           }
           self.inject_mocks('MyPlugin', mock_dict)

           # Test plugin behavior with mocks
           self.push_message('!api_test')
           self.assertIn('Mock response', self.pop_message())

Best Practices
-------------

1. **Test Isolation**: Each test should be independent and not rely on the state from other tests.

2. **Setup and Teardown**: Use ``setUp()`` to initialize your test environment and ``tearDown()`` to clean up.

3. **Timeout Handling**: Always specify appropriate timeouts for message operations to avoid hanging tests.

4. **Error Cases**: Include tests for error conditions and edge cases.

5. **Documentation**: Document your test cases to explain what they're testing and why.

Complete Example
--------------

Here's a complete example of a test suite for a plugin:

.. code-block:: python

    import unittest
    from pathlib import Path

    from errbot.backends.test import FullStackTest

    path = str(Path(__file__).resolve().parent)
    extra_plugin_dir = path

    class TestGreetingPlugin(FullStackTest):
        def setUp(self):
            super().setUp(extra_plugin_dir=extra_plugin_dir)

        def test_basic_greeting(self):
            """Test the basic greeting command."""
            self.push_message('!greet Alice')
            self.assertIn('Hello, Alice!', self.pop_message())

        def test_greeting_with_options(self):
            """Test greeting with different options."""
            # Test with count
            self.push_message('!greet Bob --count 2')
            response = self.pop_message()
            self.assertIn('Hello, Bob!Hello, Bob!', response)

            # Test with shout
            self.push_message('!greet Charlie --shout')
            self.assertIn('HELLO, CHARLIE!', self.pop_message())

        def test_error_handling(self):
            """Test how the plugin handles errors."""
            # Test missing name
            self.push_message('!greet')
            self.assertIn('Please provide a name', self.pop_message())

            # Test invalid count
            self.push_message('!greet Eve --count abc')
            self.assertIn('must be an integer', self.pop_message())


    if __name__ == '__main__':
        unittest.main()