Exception Handling
==================

Properly handling exceptions helps you build plugins that don't crash or
produce unintended side-effects when the user or your code does
something you did not expect. Combined with logging, exceptions also
allow you to get visibility of areas in which your bot is failing and
ultimately address problems to improve user experience.

Exceptions in Errbot plugins should be handled slightly differently from
how exceptions are normally used in Python. When an unhandled exception
is raised during the execution of a command, Errbot sends a message like
this:

.. code-block:: none

    Computer says nooo. See logs for details:
    <exception message here>

The above is neither helpful nor user-friendly, as the exception message
may be too technical or brief (notice there is no traceback) for the
user to understand. Even if you were to provide your own exception
message, the "Computer says nooo ..." part is neither particularly
attractive or informative.

When handling exceptions, follow these steps:

  * trap the exception as you usually would
  * log the exception inside of the ``except`` block

    * ``self.log.exception('Descriptive message here')``
    * import and use the `logging module
      <https://docs.python.org/3/howto/logging.html>`_ directly if you
      don't have access to ``self``
    * ``self.log`` is just a convenience wrapper for the standard
      Python ``logging`` module

  * send a message describing what the user did wrong and recommend a
    solution for them to try their command again
  * do not re-raise your exception in the ``except`` block as you
    normally would. This is usually done in order to produce an entry
    in the error logs, but we've already logged the exception, and by
    not re-raising it, we prevent that automatic "Computer says nooo.
    ..." message from being sent

Also, note that there is a ``errbot.ValidationException`` class which you
can use inside your helper methods to raise meaningful errors and handle
them accordingly.

Here's an example:

.. code-block:: python

    from errbot import BotPlugin, arg_botcmd, ValidationException

    class FooBot(BotPlugin):
        """An example bot"""

        @arg_botcmd('first_name', type=str)
        def add_first_name(self, message, first_name):
            """Add your first name if it doesn't contain any digits"""
            try:
                FooBot.validate_first_name(first_name)
            except ValidationException as exc:
                self.log.exception(
                    'first_name=%s contained a digit' % first_name
                )
                return 'Your first name cannot contain a digit.'

            # Add some code here to add the given name to your database

            return "Your name has been added."

        @staticmethod
        def validate_first_name(first_name):
            if any(char.isdigit() for char in first_name):
                raise ValidationException(
                    "first_name=%s contained a digit" % first_name
                )

