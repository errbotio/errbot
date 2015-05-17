Website and documentation
=========================

Err's website and documentation are built using `Sphinx`_. Please see the
section `Contributing documentation & making changes to the website <http://errbot.net/contributing/#contributing-documentation-making-changes-to-the-website>`_
on http://errbot.net for more information on how to contribute. The
information that follows here is relevant only to the project maintainers.


Publishing to GitHub pages
--------------------------

The `make gh-pages` command can be used to build output for GitHub pages. This
will pull down a copy of the repository and auto-commit to the gh-pages branch.

The results of this can then be reviewed before being pushed.


Including extra files with GitHub pages
---------------------------------------

All the files found within the `_extra` directory are copied to the root of
the output directory (after a successful Sphinx build) during the processing
of `make gh-pages`.

.. _Sphinx: http://sphinx-doc.org/
.. _reStructuredText Primer: http://sphinx-doc.org/rest.html
.. _Inline markup: http://sphinx-doc.org/markup/inline.html
