Advanced bot commands
=====================

Automatic argument splitting
----------------------------

With the `split_args_with` argument to :func:`~errbot.decorators.botcmd`,
you can specify a delimiter of the arguments and it will give you an
array of strings instead of a string:

.. code-block:: python

    @botcmd(split_args_with=' ')
    def action(self, mess, args):
        # if you send it !action one two three
        # args will be ['one', 'two', 'three']

.. note::
    `split_args_with` behaves exactly like :func:`str.split`, so you
    can use the value `None` to split on any type of whitespace, such
    as multiple spaces, tabs, etc. This is recommended over `' '` for
    general use cases.

Subcommands
-----------

If you put an _ in the name of the function, Err will create what
looks like a subcommand for you. This is useful to group commands
that belong to each other together.

.. code-block:: python

    @botcmd
    def basket_add(self, mess, args):
        # Will respond to !basket add
        pass

    @botcmd
    def basket_remove(self, mess, args):
        # Will respond to !basket remove
        pass

.. note::
    It will still respond to !basket_add and !basket_remove as well.
