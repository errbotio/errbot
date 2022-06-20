Website and documentation
=========================

Errbot's website and documentation are built using `Sphinx`_. Useful
references when contributing to the docs are the `reStructuredText Primer`_
and `Inline markup`_ documents.


Requirements
------------

Documentation *must* be built using Python 3. Additionally, extra requirements
must be installed, which may be done through `pip install -r docs/requirements.txt`
(note: you must run this from the root of the repository).

You must also have make installed in order to use the supplied Makefile.


Building and viewing locally
----------------------------

With the necessary requirements installed, the documentation can be built using
the command `make html`. Once generated, the resulting pages can be viewed by
opening `_build/html/index.html` in your webbrowser of choice.


Publishing to Read the Docs
---------------------------

*Note: This is only relevant to project maintainers*

Read the Docs should rebuild the site automatically when new commits are pushed.
When new project releases are made, it may be necessary to add the new version
and remove older versions (to prevent clutter in the version drop-down).
This can be done at https://readthedocs.org/projects/errbot/versions/.


.. _Sphinx: http://sphinx-doc.org/
.. _reStructuredText Primer: http://sphinx-doc.org/rest.html
.. _Inline markup: http://sphinx-doc.org/markup/inline.html
