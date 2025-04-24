.. warning::

   Avoid naming your plugin directory or module lib, test, or utils. These names are common in Python or used internally by some backends (e.g., Slack). Using them may cause your plugin to fail to load due to module resolution conflicts. Prefer unique, descriptive names such as lib_tools or myplugin_utils.
