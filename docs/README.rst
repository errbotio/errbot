Website and documentation
=========================

Err's website and documentation are built using `Sphinx`_. Useful references
when contributing to the docs are the `reStructuredText Primer`_ and 
`Inline markup`_ documents.

Requirements
------------

Documentation *must* be built using Python 3. Additionally, extra requirements
must be installed, which may be done through `pip install -r requirements.txt`.

You must also have make installed in order to use the supplied Makefile.

Building and viewing locally
----------------------------

With the necessary requirements installed, the documentation can be built using
the command `make html`. Once generated, the resulting pages can be viewed by
opening `_build/html/index.html` in your webbrowser of choice.

Publishing to GitHub pages
--------------------------

*Note: This is only relevant to project maintainers*

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
