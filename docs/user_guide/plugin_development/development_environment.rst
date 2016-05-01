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
repository and instructing Errbot to pull them down.

This can be achieved through the `BOT_EXTRA_PLUGIN_DIR` setting in
the `config.py` configuration file. If you set a path here pointing
to a directory on your local machine, Errbot will (recursively) scan
that directory for plugins and attempt to load any it may find.

Local test mode
---------------

You can run Errbot in a local single-user mode that does not require
any server connection by passing in the :option:`--text` (or
:option:`-T`) option flag when starting the bot.

In this mode, a very minimal back-end is used which you can interact
with directly on the command-line. It looks like this::

    $ errbot -T
    [...]
    INFO:Plugin activation done.
    Talk to  me >> _

If you have `PySide <https://pypi.python.org/pypi/PySide>`_
installed, you can also run this same mode in a separate window
using :option:`--graphic` (or :option:`-G`) instead of
:option:`--text`. The advantage of this is that you do not have the
bot's responses and log information mixed up together in the same
window.


Plugin scaffolding
------------------

Plugins consist of two parts, a special `.plug` file and one or more Python (`.py`) files
containing the actual code of your plugin
(both of these are explained in-depth in the next section).
Errbot can automatically generate these files for you
so that you do not have to write boilerplate code by hand.

To create a new plugin, run `errbot --new-plugin`
(optionally specifying a directory where to create the new plugin -
it will use the current directory by default).
It will ask you a few questions such as the name for your plugin,
a description and which versions of errbot it will work with and
generate a plugin skeleton from this with all the information
filled out automatically for you.
