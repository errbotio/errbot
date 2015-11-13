Development environment
=======================

Before we dive in and start writing our very first plugin, I'd like
to take a moment to show you some tools and features which help
facilitate the development process.

Loading plugins from a local directory
--------------------------------------

Normally, you manage and install plugins through the built-in
`!repos` command. This installs plugins by cloning them via git, and
allows updating of them through the `!repos update` command.

During development however, it would be easier if you could load
your plugin(s) directly, without having to commit them to a Git
repository and instructing Err to pull them down. 

This can be achieved through the `BOT_EXTRA_PLUGIN_DIR` setting in
the `config.py` configuration file. If you set a path here pointing
to a directory on your local machine, Err will (recursively) scan
that directory for plugins and attempt to load any it may find.

Local test mode
---------------

You can run Err in a local single-user mode that does not require
any server connection by passing in the :option:`--text` (or
:option:`-T`) option flag when starting the bot.

In this mode, a very minimal back-end is used which you can interact
with directly on the command-line. It looks like this::

    $ err.py --text
    [...]
    INFO:Plugin activation done.
    Talk to  me >> _

If you have `PySide <https://pypi.python.org/pypi/PySide>`_
installed, you can also run this same mode in a separate window
using :option:`--graphic` (or :option:`-G`) instead of
:option:`--text`. The advantage of this is that you do not have the
bot's responses and log information mixed up together in the same
window.

Plugin skeleton
---------------

We also provide a very `minimal plugin
<https://github.com/zoni/err-skeleton>`_ which shows the basic
layout of a simple plugin. You can save yourself some time writing
boilerplate code by using this template as a starting point.
