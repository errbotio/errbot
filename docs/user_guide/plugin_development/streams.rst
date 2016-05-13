Streams
=======

Streams are file transferts. It can be used to store documents, index them, send generated content on the fly etc.

Waiting for incoming file transferts
------------------------------------

The bot can be send files from the users. You just have to implement the
:func:`~errbot.botplugin.BotPlugin.callback_stream` method on your plugin to be notified for new incoming file
tranfer requests.

Note: note all backends supports this, check if it has been correctly implemented from the backend itself.

For example, getting the initiator of the transfer and the content, see :class:`~errbot.backends.base.Stream` for
more info about the various fields.

.. code-block:: python

    from errbot import BotPlugin, botcmd

    class PluginExample(BotPlugin):

        def callback_stream(self, stream):
            self.send(stream.identifier, "File request from :" + str(stream.identifier))
            stream.accept()
            self.send(stream.identifier, "Content:" + str(stream.fsource.read()))


Sending a file to a user or a room
----------------------------------


You can use :func:`~errbot.botplugin.BotPlugin.send_stream_request` to initiate a transfer:

.. code-block:: python

    stream = self.send_stream_request(msg.frm, open('/tmp/myfile.zip', 'r'), name='bills.zip', stream_type='application/zip')

The returned stream object can be used to monitor the progress of the transfer with `stream.status`, `stream.transfered` etc...
See :class:`~errbot.backends.base.Stream` for more details.

