Mentions
========

Depending on the backend used, users can mention and notify other users by using a special syntax like `@gbin`.
With this feature, a plugin can listen to the mentioned users in the chat.

How to use it
-------------

Here is an example to listen to every mentions and reports them back on the chat.

.. code-block:: python

    from errbot import BotPlugin

    class PluginExample(BotPlugin):

        def callback_mention(self, message, mentioned_people):
            for identifier in mentioned_people:
                self.send(message.frm, 'User %s has been mentioned' % identifier)


Identifying if the bot itself has been mentioned
------------------------------------------------

Simply test the presence of the bot identifier within the `mentioned_people` :

.. code-block:: python

    from errbot import BotPlugin

    class PluginExample(BotPlugin):

        def callback_mention(self, message, mentioned_people):
            if self.bot_identifier in mentioned_people:
                self.send(message.frm, 'Errbot has been mentioned !')

