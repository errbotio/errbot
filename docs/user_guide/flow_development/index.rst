Flow development
================

Flows are a feature in Errbot to enable plugin designers to chain several plugin commands together into a "conversation".

For example, imagine interacting with a bot that needs more that one command, like setting up a poll in a
chatroom::

  User: !poll new Where do we go for lunch ?

  Bot: Flow poll_setup started, you can continue with:
       !poll newoption <your option>

  User: !poll newoption Greek

  Bot: Option added, current options:
       - Greek

  Bot: You can continue with:
       !poll newoption <your option>
       !poll start

  User: !poll newoption French

  Bot: Option added, current options:
       - Greek
       - French

  Bot: You can continue with:
       !poll newoption <your option>
       !poll start

  User: !poll start
  [...]

In this guide we will explain the underlying concepts and basics of writing flows.
Prerequisite: you need to be familiar with the normal errbot plugin development.


.. toctree::
  :maxdepth: 2
  :numbered:

  concepts
  basics
  advanced
