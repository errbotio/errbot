[Advanced] Backend development
==============================

A backend is the glue code to connect Errbot to a chatting service.
Starting with Errbot 2.3.0, backends can be developed out of the main repository.
This documentation is there to guide you making a new backend for a chatting
service but is also interesting to understand more core concepts of Errbot.

It is important to understand the core concepts of Errbot before
starting to work on a backend.

Architecture
------------

Backends are just a specialization of the bot, they are what
is instanciated as the bot and are the entry point of the bot.

Following this logic a backend must inherit from
:class:`~errbot.errBot.ErrBot`.

:class:`~errbot.errBot.ErrBot` inherits itself from
:class:`~errbot.backends.base.Backend`. This is where you can
find what Errbot is expecting from backend.

You'll see a series of methods simply throwing the exception
:class:`NotImplementedError`.
Those are the one you need to implement to fill up the blanks.

Identifiers
-----------

Every backend have a very specific way of addressing who, where
and how to speak to somebody.

Lifecycle: identifiers are either created internally by the backend
or externally by the plugins from
:func:`~errbot.backends.base.Backend.build_identifier`.

There are 2 types of identifiers:

- a person
- a person in a chatroom


Identifier for a person
-----------------------

It is important to note that for some backends you can infer what
a person is from what a person in a chatroom is, but for privacy
reason you cannot on some backends ie. you can send a private
message to a person in a chatroom but if the person leaves the room
you have no way of knowing how to contact her/him personally.

Backends must implement a specific Identifier class that matches
their way of identifying those.

For example Slack has a notion of userid and channeid you can find
in the :class:`~errbot.backends.slack.SlackIdentifier` which is
completely opaque to ErrBot itself.

But you need to implement a mapping from those private parameters
to those properties:

- person: this needs to be a string that identifies a person.
  This should be enough info for the backend to contact this person.
  This should be a *secure* and sure way to identify somebody.
- client: this will identify optionally as a string additional
  information or channel from where this person is sending a message.
  For example, some backends open a one to one room to chat, or some
  backends identifies the current peripheral from which the person is
  sending a message from (mobile, web, ...)

Some of those strings are completely unreadable for humans ie. `U00234FBE`
for a person. So you need to provide more human readable info:

- nick: this would be the short name refering to that person. ie. `gbin`
- displayName: (optionally) this would give for example a full name
  ie. `Guillaume Binet`. This is often found in professional chatting services.


Identifier for a person in a chatroom
-------------------------------------

This is simply an Identifier with an added property: room.
The string representation of room should give a chatroom identifier (see below).

See for example :class:`~errbot.backends.slack.SlackMUCIdentifier`

Chatrooms / MUCRooms
--------------------

In order to implement the various MUC related APIs you'll find from
:class:`~errbot.backends.base.Backend`, you'll need to implement a Room class.
To help guide you, you can inherit from :class:`~errbot.backends.base.MUCRoom`
and fill up the blanks from the NotImplementedError.

Lifecycle: Those are created either internally by the backend or externally
through :func:`~errbot.backends.base.Backend.join_room` from a string identifier.
