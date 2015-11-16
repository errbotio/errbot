Logging to Sentry
=================

According to the `official website <https://www.getsentry.com/about/>`_...

    Sentry is an event logging platform primarily focused on capturing and
    aggregating exceptions.

    It was originally conceived at DISQUS in early 2010 to solve exception
    logging within a Django application. Since then it has grown to support
    many popular languages and platforms, including Python, PHP, Java, Ruby,
    Node.js, and even JavaScript.

Come again? Just what is Sentry, exactly?
-----------------------------------------

The `official documentation <http://sentry.readthedocs.org/en/latest/index.html>`_
explains it better:

    Sentry is a realtime event logging and aggregation platform. At its core it
    specializes in monitoring errors and extracting all the information needed
    to do a proper post-mortem without any of the hassle of the standard user
    feedback loop.

If that sounds like something you'd want to gift your precious Errbot instance with,
then do keep on reading :)

Setting up Sentry itself
------------------------

Installing and configuring sentry is beyond the scope of this document. However,
there are two options available to you. You can either get a
`hosted account <https://www.getsentry.com/pricing/>`_, or grab the code and
`run your own server <http://sentry.readthedocs.org/en/latest/index.html>`_ instead.

Configuring Errbot to use Sentry
--------------------------------

Once you have an instance of Sentry available, you'll probably want to create a
team specifically for Errbot first.

When you have, you should be able to access a page called "Client configuration".
There, you will be presented with a so-called DNS value, which has the following format:

    http://0000000000000000:000000000000000000@sentry.domain.tld/0

To setup Errbot with Sentry:

* Open up your bot's config.py
* Set **BOT_LOG_SENTRY** to *True* and fill in **SENTRY_DSN** with the DNS value obtained previously
* Optionally adjust **SENTRY_LOGLEVEL** to the desired level
* Restart Errbot

You should now see Exceptions and log messages show up in your Sentry stream.
