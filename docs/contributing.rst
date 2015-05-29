Contributing
============

If you would like to contribute to the project, please do not hesitate to get
involved! Here you can find how best to get started.

Contributing to Err itself
--------------------------

All development on Err happens on GitHub_. If you'd like to get involved, just
fork_ the repository and make changes in your own repo. When you are satisfied
with your changes, just open a `pull request`_ with us and we'll get it reviewed
as soon as we can! Depending on our thoughts, we might decide to merge it in
right away, or we may ask you to change certain parts before we will accept the
change.

In order to make the process as easy for everyone involved, please follow
these guidelines as you open a pull request.

* Make your changes on a separate branch_, preferably giving it a descriptive name.
* Split your work up into smaller commits if possible, while making sure each commit
  can still function on it's own. Do not commit work-in-progress code, commit it
  once it's working.
* Run the test-suite before opening your pull request, and make sure all tests pass.
  You can run the tests with :command:`python run_tests.py` in the root of the
  repository.
* If you can, please add tests for your code. We know large parts of our codebase
  are missing tests, so we won't reject your code if it lacks tests, though.

Contributing documentation & making changes to the website
----------------------------------------------------------

`errbot.net <http://www.errbot.net/>`_ is created using Sphinx_, which also doubles
as a generator for our (API) documentation. The code for it is in the same repository
as err itself, inside the docs_ folder. To make changes to the documentation or the
website, you can build the HTML locally as follows::

    # Change directory into the docs folder
    cd docs/
    # Install the required extra dependencies
    pip install -r requirements.txt
    # Generate the static HTML
    make html
    # Then, open the generated _build/html/index.html in a browser

The content you find on the website is kept in a branch called
`errbot.net <https://github.com/gbin/err/tree/errbot.net/docs>`_.
The master branch is merged back into this branch with each official release of Err.
This way, the API documentation on the site always reflects the version of the code
found on PyPI rather than something that is in development but not yet released.

When making changes to the documentation, please base your branch off the `errbot.net`
branch and open a pull request with us as described in the previous section.

.. note::
    Useful references on working with sphinx and reStructuredText are the
    `reStructuredText Primer`_ and `Inline markup`_ documents.

.. note::
    You must run Sphinx with Python 3, Python 2 is unsupported.

Contributing plugins
--------------------

If you've written a cool plugin of your own and would like to see it included in
the repositories, please send us a pull request after adding it to repos.py_.

Issues and feature requests
===========================

Please report issues or feature requests on the `issue tracker`_ on GitHub.

When reporting issues, please be as specific as possible. Include things such as
your Python version, platform, debug logs, and a description of what is happening.
If you can tell us how to reproduce the issue ourselves, this makes it a lot
easier for us to figure out what is going on, as well.

Getting help
============

For general help with Err, you can post in our `Google Plus community`_ or
visit our Gitter_ channel.

.. _GitHub: https://github.com/gbin/err
.. _fork: https://github.com/gbin/err/fork
.. _`pull request`: https://help.github.com/articles/using-pull-requests
.. _branch: http://git-scm.com/book/en/Git-Branching
.. _Sphinx: http://sphinx-doc.org/
.. _docs: https://github.com/gbin/err/tree/errbot.net/docs/
.. _repos.py: https://github.com/gbin/err/blob/master/errbot/repos.py
.. _`issue tracker`: https://github.com/gbin/err/issues/
.. _`Google Plus community`: https://plus.google.com/communities/117050256560830486288
.. _reStructuredText Primer: http://sphinx-doc.org/rest.html
.. _Inline markup: http://sphinx-doc.org/markup/inline.html
.. _Gitter: http://gitter.im/gbin/err/
