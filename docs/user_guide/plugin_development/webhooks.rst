Webhooks
========

Errbot has a small integrated webserver that is capable of hooking up
endpoints to methods inside your plugins.

You must configure the *Webserver* plugin before this functionality
can be used. You can get the configuration template using `!plugin config
Webserver`, from where it's just a simple matter of plugging in the
desired settings.

.. note::
    There is a `!generate certificate` command to generate a
    self-signed certificate in case you want to enable SSL
    connections and do not have a certificate.

.. warning::
    It is not recommended to expose Errbot's webserver directly to the
    network. Instead, we recommend placing it behind a webserver
    such as `nginx <http://nginx.org/>`_ or `Apache <https://httpd.apache.org/>`_.


Simple webhooks
---------------

All you need to do for a plugin of yours to listen to a specific URI
is to apply the :func:`~errbot.webhook` decorator to your method.
Whatever it returns will be returned in response to the request:

.. code-block:: python

    from errbot import BotPlugin, webhook

    class PluginExample(BotPlugin):
        @webhook
        def test(self, request):
            self.log.debug(repr(request))
            return "OK"

This will listen for POST requests on
http://yourserver.tld:yourport/test/, and return *"OK"* as the
response body.

.. note::
    If you return `None`, an empty 200 response will be sent.


You can also set a custom URI pattern by providing the `uri_rule`
parameter:

.. code-block:: python

    from errbot import BotPlugin, webhook

    class PluginExample(BotPlugin):
        @webhook('/example/<name>/<action>/')
        def test(self, request, name, action):
            return "User %s is performing %s" % (name, action)

Refer to the documentation on Flask's
`route <http://flask.pocoo.org/docs/1.0/api/#flask.Flask.route>`_
for details on the supported syntax
(Errbot uses Flask internally).


Handling JSON request
---------------------

If an incoming request has the MIME media type set to `application/json`
the request will automatically be decoded as JSON.
You will receive the result of calling `json.loads()` on `request` automatically
so that you won't have to do this yourself.


Handling form-encoded requests
------------------------------

Form-encoded requests (those with an
*application/x-www-form-urlencoded* mimetype) are very simple to
handle as well, you just need to specify the `form_param` parameter.

A good example for this is the GitHub format which posts a form with
a *payload* parameter:

.. code-block:: python

    from errbot import BotPlugin, webhook

    class Github(BotPlugin):
        @webhook('/github/', form_param = 'payload')
        def notification(self, payload):
            for room in self.bot_config.CHATROOM_PRESENCE:
                self.send(
                    self.build_identifier(room),
                    'Commit on %s!' % payload['repository']['name'],
                )


The raw request
---------------

The above webhooks are convenient for simple tasks, but sometimes
you might wish to have more power and have access to the actual
request itself. By setting the `raw` parameter of the
:func:`~errbot.decorators.webhook` decorator to `True`, you will
be able to get the
`flask.Request <http://flask.pocoo.org/docs/1.0/api/#flask.Request>`_
which contains all the details about the actual request:

.. code-block:: python

    from errbot import BotPlugin, webhook

    class PluginExample(BotPlugin):
        @webhook(raw=True)
        def test(self, request):
            user_agent = request.headers.get("user-agent", "Unknown")
            return f"Your user-agent is {user_agent}"


Returning custom headers and status codes
-----------------------------------------

Adjusting the response headers, setting cookies or returning a
different status code can all be done by manipulating the
`flask response <http://flask.pocoo.org/docs/1.0/patterns/deferredcallbacks/>`_
object. The Flask docs on `the response object
<http://flask.pocoo.org/docs/1.0/api/#response-objects>`_
explain this in more detail. Here's an example of setting a
custom header:

.. code-block:: python

    from errbot import BotPlugin, webhook
    from flask import after_this_request

    class PluginExample(BotPlugin):
        @webhook
        def example(self, incoming_request):
            @after_this_request
            def add_header(response):
                response.headers['X-Powered-By'] = 'Errbot'
            return "OK"

Flask also has various helpers such as the `abort()` method.
Using this method we could, for example, return a 403 forbidden
response like so:

.. code-block:: python

    from errbot import BotPlugin, webhook
    from flask import abort

    class PluginExample(BotPlugin):
        @webhook
        def example(self, incoming_request):
            abort(403, "Forbidden")


Testing a webhook through chat
------------------------------

You can use the `!webhook` command to test webhooks without making
an actual HTTP request, using the following format::

    !webhook test /[endpoint] [post_content]

For example::

    !webhook test /test

    !webhook test /github payload=%7B%22pusher%22%3A%7B%22name%22%3A%22gbin%22%2C%22email%22%3A%22gbin%40gootz.net%22%7D%2C%22repository%22%3A%7B%22name%22%3A%22test%22%2C%22created_at%22%3A%222012-08-12T16%3A09%3A43-07%3A00%22%2C%22has_wiki%22%3Atrue%2C%22size%22%3A128%2C%22private%22%3Afalse%2C%22watchers%22%3A0%2C%22url%22%3A%22https%3A%2F%2Fgithub.com%2Fgbin%2Ftest%22%2C%22fork%22%3Afalse%2C%22pushed_at%22%3A%222012-08-12T16%3A26%3A35-07%3A00%22%2C%22has_downloads%22%3Atrue%2C%22open_issues%22%3A0%2C%22has_issues%22%3Atrue%2C%22stargazers%22%3A0%2C%22forks%22%3A0%2C%22description%22%3A%22ignore%20this%2C%20this%20is%20for%20testing%20the%20new%20err%20github%20integration%22%2C%22owner%22%3A%7B%22name%22%3A%22gbin%22%2C%22email%22%3A%22gbin%40gootz.net%22%7D%7D%2C%22forced%22%3Afalse%2C%22after%22%3A%22b3cd9e66e52e4783c1a0b98fbaaad6258669275f%22%2C%22head_commit%22%3A%7B%22added%22%3A%5B%5D%2C%22modified%22%3A%5B%22README.md%22%5D%2C%22timestamp%22%3A%222012-08-12T16%3A24%3A25-07%3A00%22%2C%22removed%22%3A%5B%5D%2C%22author%22%3A%7B%22name%22%3A%22Guillaume%20BINET%22%2C%22username%22%3A%22gbin%22%2C%22email%22%3A%22gbin%40gootz.net%22%7D%2C%22url%22%3A%22https%3A%2F%2Fgithub.com%2Fgbin%2Ftest%2Fcommit%2Fb3cd9e66e52e4783c1a0b98fbaaad6258669275f%22%2C%22id%22%3A%22b3cd9e66e52e4783c1a0b98fbaaad6258669275f%22%2C%22distinct%22%3Atrue%2C%22message%22%3A%22voila%22%2C%22committer%22%3A%7B%22name%22%3A%22Guillaume%20BINET%22%2C%22username%22%3A%22gbin%22%2C%22email%22%3A%22gbin%40gootz.net%22%7D%7D%2C%22deleted%22%3Afalse%2C%22commits%22%3A%5B%7B%22added%22%3A%5B%5D%2C%22modified%22%3A%5B%22README.md%22%5D%2C%22timestamp%22%3A%222012-08-12T16%3A24%3A25-07%3A00%22%2C%22removed%22%3A%5B%5D%2C%22author%22%3A%7B%22name%22%3A%22Guillaume%20BINET%22%2C%22username%22%3A%22gbin%22%2C%22email%22%3A%22gbin%40gootz.net%22%7D%2C%22url%22%3A%22https%3A%2F%2Fgithub.com%2Fgbin%2Ftest%2Fcommit%2Fb3cd9e66e52e4783c1a0b98fbaaad6258669275f%22%2C%22id%22%3A%22b3cd9e66e52e4783c1a0b98fbaaad6258669275f%22%2C%22distinct%22%3Atrue%2C%22message%22%3A%22voila%22%2C%22committer%22%3A%7B%22name%22%3A%22Guillaume%20BINET%22%2C%22username%22%3A%22gbin%22%2C%22email%22%3A%22gbin%40gootz.net%22%7D%7D%5D%2C%22ref%22%3A%22refs%2Fheads%2Fmaster%22%2C%22before%22%3A%2229b1f5e59b7799073b6d792ce76076c200987265%22%2C%22compare%22%3A%22https%3A%2F%2Fgithub.com%2Fgbin%2Ftest%2Fcompare%2F29b1f5e59b77...b3cd9e66e52e%22%2C%22created%22%3Afalse%7D

.. note::
    You can get a list of all the endpoints with the `!webstatus`
    command.
