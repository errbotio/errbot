Gitter Backend
==============

This is a backend for `Gitter <http://gitter.im>`_ for errbot.
The source code is hosted on `github <https://github.com/errbotio/err-backend-gitter>`_.

`Screenshot <https://raw.githubusercontent.com/errbotio/err-backend-gitter/master/screenshot.png>`_.

Requirements
------------

 - A github account to be used by the bot.
 - The client id and client secret, received when `authorising <https://developer.gitter.im/docs/authentication>`_ the bot as gitter application or a personal access token.

Installation
------------

Checkout the backend using git:

.. codeblock:: bash
  git checkout https://github.com/errbotio/err-backend-gitter

Edit errbot's configuration file (``config.py``) and set the backend and backend directory variables:

.. codeblock:: none
  BACKEND = 'Gitter'
  BOT_EXTRA_BACKEND_DIR = '/path_to/backend'

Authentication
--------------
From there you have can either add an application or use a personal token from a user reserved to the bot.

Adding an application, workflow for auth
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
1. pip install bottle requests
2. execute the script: ./oauth.py and it will guide you

Adding as a real user
~~~~~~~~~~~~~~~~~~~~~
1. authenticate as the bot user (new incognito window helps ;) )
2. go visit https://developer.gitter.im/apps
3. use directly the token like this in you config.py

.. codeblock:: none
  BOT_IDENTITY = {
      'token' : '54537fa855b9a7bbbbbbbbbc568ea7c069d8c34d'
  }

Contributing
------------
1. Fork it!
2. Create your feature branch: `git checkout -b my-new-feature``
3. Commit your changes: ``git commit -am 'Add some feature'``
4. Push to the branch: ``git push origin my-new-feature``
5. Submit a pull request :D
