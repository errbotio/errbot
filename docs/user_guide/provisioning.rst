Provisioning (advanced)
=======================

Plugins can be configured by talking to the bot with::

    !plugin config my_plugin {'key': 'value'}

Also plugins can store values in the storage as key value pairs.

Sometimes, you need to inject those values either config or plugin state
ahead of time for example at errbot installation (also called provisioning).

It is useful for installation scripts and deployments.

.. note::
   When using the default "Shelf storage", errbot may not be running when 
   attempting to get or set data. Any attempt to do so while the bot is 
   running will result in the error "Storage does not appear to have been 
   opened yet" being returned. This is caused by the fact that the python
   `shelve` module only allows a single process to hold the database open.
   For further details, see the 
   `shelve docs <https://docs.python.org/3/library/shelve.html#restrictions>`_.


Reading stored values
---------------------

To read the current stored plugin configs you can do from the command line::

    errbot --storage-get core

It will give you on stdout a python dictionary of the core namespace like::

    {'configs': {'Webserver': {'PORT': 8888}}}

To read the values from a plugin storage, for example here from alimac/err-factoid you can do::

    errbot --storage-get Factoid

It will give you on stdout a similar output::

    {'FACTOID': {'fire': 'burns', 'water': 'wet'}}


Writing values
--------------

To add or change specific values without touching others you can merge a dictionary like that::

    echo "{'configs': {'Webserver': {'PORT': 9999}}}" | errbot --storage-merge core

Checking back::

    errbot --storage-get core
    {'configs': {'Webserver': {'PORT': 9999}}}

Changing facts in Factoid (note the merge is only on the first level so we change all FACTOID here)::

    echo "{'FACTOID': {'errbot': 'awesome'}}" | errbot --storage-merge Factoid

    >>> !errbot?
    errbot is awesome

You can use --storage-set in the same fashion but it will erase first the namespace before writing your values.
