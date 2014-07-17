Intro
=====

Before we get started I would like to make sure you have all the
necessary requirements installed and give you an idea of which
knowledge you should already possess in order to follow along
without difficulty.

XMPP versus IRC
---------------

Err was initially built for `XMPP <http://xmpp.org/about-xmpp/>`_
networks, with `IRC <http://tools.ietf.org/html/rfc2810>`_ support
being added later. As such, some Jabberisms shine through in the
various interfaces. 

Most of the contents of this guide apply equally to both the XMPP
and IRC back-ends. Items that are specific to a certain back-end
however will have this clearly noted.

Requirements
------------

This guide assumes that you've already installed and configured Err
and have successfully managed to connect it to an XMPP or IRC
server. See :doc:`/user_guide/setup` if you have not yet managed to
install or start Err.

Prior knowledge
---------------

It is assumed that you have some experience with the `Python
<http://pytest.org/>`_ programming language. You can most definitely
work with Err if you only have basic Python knowledge, but you
should know about data structures such as dictionaries, tuples and
lists, know what docstrings are and have a basic understanding of
decorators.

You should also have some basic familiarity with the `Extensible
Messaging and Presence Protocol (XMPP)
<http://xmpp.org/about-xmpp/>`_. Err provides high-level APIs for
most tasks so if you know what Jabber IDs are, understand how
resources and priorities relate to each other and have an
understanding of the concept of Multi User Chatrooms (MUC), you
should not have any difficulties.
