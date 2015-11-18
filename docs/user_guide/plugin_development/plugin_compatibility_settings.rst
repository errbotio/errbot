Plugin compatibility settings
=============================


Python compatibility
--------------------

Your plugin might not be compatible with Python 2 or Python 3.
In order to prevent users to install them under an incompatible environment,
you can add a **Python** section to your plug file:

.. code-block:: ini

    [Core]
    Name = MyPlugin
    Module = myplugin

    [Documentation]
    Description = my plugin

    [Python]
    Version=2+

The possible choices for **Version** are:

- 2 : only compatible with Python 2
- 3 : only compatible with Python 3
- 2+: compatible with both

Of there is no Python section, your plugin will be restricted to Python 2 for backward compatibility.


Errbot compatibility
--------------------

Sometimes when your plugin breaks under a specific version of Errbot, you
might want to warn the user of your plugin and not load it.


You can do it by adding an **Errbot** section to your plug file like this:

.. code-block:: ini

    [Core]
    Name = MyPlugin
    Module = myplugin

    [Documentation]
    Description = my plugin

    [Errbot]
    Min=2.4.0
    Max=2.6.0

If the **Errbot** section is omitted, it defaults to "compatible with any version".

If the **Min** option is omitted, there is no minimum version enforced.

If the **Max** option is omitted, there is no maximum version enforced.

Versions need to be a 3 dotted one (ie 2.4 is not allowed but 2.4.0 is). And it understands
those suffixes:

- "-beta"
- "-rc1"
- "-rc2"
- etc.

For example: 2.4.0-rc1

note: -beta1 or -rc are illegal. Only rc can get a numerical suffix.
