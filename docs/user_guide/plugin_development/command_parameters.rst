Command Parameters
==================

This page explains how to handle command parameters in Errbot plugins, including default values, argument parsing, and best practices.

Basic Command Parameters
------------------------

The most basic form of a bot command takes a message object and arguments:

.. code-block:: python

    @botcmd
    def hello(self, msg, args):
        return f"Hello! You said: {args}"

In this case, ``msg`` is the message object containing information about who sent the command and where, and ``args`` is a string containing everything after the command.

Default Values
--------------

You can provide default values for command parameters. This is useful when you want to make certain arguments optional:

.. code-block:: python

    @botcmd
    def echo(self, msg, args="default message"):
        return f"You said: {args}"

In this example, if someone calls the command without arguments, ``args`` will be set to "default message".

.. note::
    Default values work for both the ``msg`` and ``args`` parameters. However, it's recommended to only use default values for ``args`` as the ``msg`` parameter is typically required for proper command handling.

Argument Splitting
------------------

You can automatically split arguments into a list using the ``split_args_with`` parameter:

.. code-block:: python

    @botcmd(split_args_with=None)  # Split on any whitespace
    def count(self, msg, args):
        # If user types: !count one two three
        # args will be ['one', 'two', 'three']
        return f"You provided {len(args)} arguments"

The ``split_args_with`` parameter works exactly like Python's ``str.split()``. Common values are:

- ``None``: Split on any whitespace (recommended for most cases)
- ``' '``: Split on single spaces only
- ``','``: Split on commas
- ``'|'``: Split on pipe characters

Advanced Argument Parsing
-------------------------

For more complex argument parsing, you can use the ``arg_botcmd`` decorator which provides argparse-style argument handling:

.. code-block:: python

    @arg_botcmd('name', type=str)
    @arg_botcmd('--count', dest='repeat', type=int, default=1)
    def repeat(self, msg, name=None, repeat=None):
        return name * repeat

This allows for:
- Type checking and conversion
- Optional arguments with defaults
- Named arguments
- Help text generation

Best Practices
--------------

1. **Parameter Order**: Always keep parameters in the order ``(self, msg, args)`` for consistency.

2. **Default Values**: Use default values for optional parameters, but be careful with the ``msg`` parameter as it's usually required.

3. **Argument Splitting**: Use ``split_args_with=None`` when you need to handle multiple space-separated arguments.

4. **Type Safety**: Use ``arg_botcmd`` when you need type checking or complex argument parsing.

5. **Documentation**: Always document your command's parameters and expected usage in the function's docstring.

Example with All Features
-------------------------

Here's a complete example showing various parameter handling techniques:

.. code-block:: python

    @arg_botcmd('name', type=str, help='The name to greet')
    @arg_botcmd('--count', dest='repeat', type=int, default=1, help='Number of times to repeat')
    @arg_botcmd('--shout', dest='shout', action='store_true', help='Convert to uppercase')
    def greet(self, msg, name=None, repeat=None, shout=False):
        """Greet someone with a customizable message.
        
        Example:
            !greet Alice --count 3 --shout
        """
        if not name:
            return "Please provide a name to greet"
            
        message = f"Hello, {name}!"
        if shout:
            message = message.upper()
            
        return message * repeat

This command demonstrates:
- Required and optional arguments
- Type conversion
- Default values
- Boolean flags
- Help text
- Proper documentation

Common Pitfalls
---------------

1. **Default Values for msg**: While possible, it's generally not recommended to provide default values for the ``msg`` parameter as it's essential for command context.

2. **Argument Splitting**: Remember that ``split_args_with=None`` splits on any whitespace, which might not be what you want if you need to preserve spaces in arguments.

3. **Type Conversion**: When using ``arg_botcmd``, always specify the correct type for arguments to ensure proper conversion and validation.

4. **Parameter Names**: Keep parameter names consistent with the decorator's expectations (``msg`` and ``args`` for basic commands, or the names specified in ``arg_botcmd``).

5. **Documentation**: Always include examples in your docstrings to help users understand how to use your commands correctly. 