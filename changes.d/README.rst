Changelog Fragments
===================
This directory contains changelog fragments managed by scriv.
How to Add a Changelog Entry
-----------------------------
When you make a change that should be noted in the changelog, create a new
fragment file using scriv:
.. code-block:: bash
    scriv create
This will create a new file in this directory with a template. Edit the file
to describe your change under the appropriate category:
- **Features**: New features and improvements
- **Bug Fixes**: Bug fixes
- **Documentation**: Documentation improvements
- **Deprecations and Removals**: Deprecations and removals
- **Miscellaneous**: Other changes
Example
-------
After running ``scriv create``, you'll get a file like
``changelog.d/20251013_120000_username.rst``. Edit it to look like:
.. code-block:: rst
    Features
    --------
    - Add support for threaded replies in Discord backend. (#123)
    Bug Fixes
    ---------
    - Fix memory leak in plugin storage mechanism. (#456)
Only include the categories that apply to your change. You can delete the
categories you don't need.
Linking to Issues
-----------------
When referencing GitHub issues or pull requests, use RST link syntax:
.. code-block:: rst
    - Your change description. (#123)
Building the Changelog
-----------------------
Maintainers will collect all fragments into the main CHANGES.rst file using:
.. code-block:: bash
    scriv collect --version X.Y.Z
