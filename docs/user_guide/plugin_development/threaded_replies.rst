Threaded Replies
===============

Errbot supports threaded replies, which allows bot responses to be organized in conversation threads when the backend supports this feature. This is particularly useful for maintaining context in group chats and keeping related messages together.

Enabling Threaded Replies
------------------------

There are two ways to enable threaded replies in Errbot:

1. Per-command basis using the `in_reply_to` parameter in `send`
2. Globally for specific commands using the `DIVERT_TO_THREAD` configuration

Per-command Threaded Replies
---------------------------

You can send a threaded reply to any message using the `in_reply_to` parameter in `send`:

.. code-block:: python

    from errbot import BotPlugin, botcmd

    class ThreadedPlugin(BotPlugin):
        @botcmd
        def threaded_response(self, msg, args):
            # This response will be sent as a threaded reply
            self.send(msg.frm, "This is a threaded response", in_reply_to=msg)

Global Thread Configuration
-------------------------

You can configure Errbot to automatically send responses in threads for specific commands by adding them to the `DIVERT_TO_THREAD` configuration in your config.py:

.. code-block:: python

    # Send all responses for 'help' and 'about' commands in threads
    DIVERT_TO_THREAD = ("help", "about")

    # Or send all command responses in threads
    DIVERT_TO_THREAD = ("ALL_COMMANDS",)

Backend Support
--------------

Threaded replies are supported by the following backends:

- Slack
- Discord
- Matrix
- Telegram (in group chats)

Note that not all backends support threaded replies. If a backend doesn't support threading, the message will be sent as a regular message.

Best Practices
-------------

1. Use threaded replies for:
   - Long conversations that need to maintain context
   - Command responses that might generate multiple messages
   - Group chat discussions where keeping related messages together is important

2. Consider using threaded replies for:
   - Help commands
   - Status updates
   - Multi-step processes
   - Debug information

Example Plugin
-------------

Here's a complete example of a plugin that demonstrates threaded replies:

.. code-block:: python

    from errbot import BotPlugin, botcmd
    import time

    class ThreadedExample(BotPlugin):
        @botcmd
        def status(self, msg, args):
            """Get the current status with updates in a thread"""
            self.send(msg.frm, "Starting status check...", in_reply_to=msg)
            time.sleep(1)
            self.send(msg.frm, "Checking system resources...", in_reply_to=msg)
            time.sleep(1)
            self.send(msg.frm, "Status check complete!", in_reply_to=msg)

        @botcmd
        def help_threaded(self, msg, args):
            """Get help in a thread"""
            help_text = """
            Available commands:
            - !status: Get system status
            - !help_threaded: Show this help message
            """
            self.send(msg.frm, help_text, in_reply_to=msg)

Configuration
------------

To enable threaded replies globally for specific commands, add them to your config.py:

.. code-block:: python

    # Send all responses for these commands in threads
    DIVERT_TO_THREAD = (
        "help",
        "about",
        "status",
        "debug"
    )

    # Or send all command responses in threads
    DIVERT_TO_THREAD = ("ALL_COMMANDS",)

Limitations
----------

1. Not all backends support threaded replies
2. Threaded replies may not be visible in all chat clients
3. Some backends may have limitations on thread depth or length
4. Threaded replies may not be preserved in chat history the same way as regular messages

When using threaded replies, it's important to test the behavior with your specific backend and chat client to ensure the feature works as expected. 