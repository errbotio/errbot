err - the pluggable jabber bot
==============================

err is a plugin based XMPP chatbot designed to be easily deployable, extensible and maintainable.
It is written in python and it is based on jabberbot_ and yapsy_ with some minor modifications for the first one.


**Brief History**

At Mondial Telecom (http://www.mondialtelecom.be), we needed a chat bot over XMPP so it can reach the non techie audience of the company.
We started to write so much features that we decided to make a more modular bot framework.

**Features**

- Tested with hipchat_ and openfire_ but should be compatible with any XMPP/Jabber servers.
- Can be setup so a restricted list of persons have the administration rights
- Dynamic plugin architecture : the bot admin can install/uninstall/enable/disable plugins dynamically just by chatting with the bot.
- Supports MUCs (chatrooms)
- Can proxy and route one 2 one messages to MUC so it can enabler simpler XMPP notifiers to be MUC compatible (for example the jira XMPP notifier).
- Really easily extensible (see example below)
- Provides an an automatic persistance store per plugin
- an !help command that generate dynamically the documentation from the python docstrings of the commands

.. _hipchat: http://www.hipchat.org/
.. _openfire: http://www.igniterealtime.org/projects/openfire/
.. _jabberbot: http://thp.io/2007/python-jabberbot/
.. _yapsy: http://yapsy.sourceforge.net/


**Installation**

Dependencies (for example with pip but if you can have them from your standard distro it is better)::
    pip install Yapsy
    pip install xmpppy



Create a user for the bot in your XMPP server admin.

From the installation directory copy::
    cp config-template.py config.py

Read the inline documentation of the file and edit the values so the bot can connect to your XMPP server

**Starting the daemon**

For a one shot try, I would recommend to use::
    ./err.py

so you can inspect the logs for an immediate feedback

Then at deployment time, a nohup utility script can be used::
    ./err.sh

**Interact with the Bot**

- Invite the bot directly from your chat client.
- Send "!help" to it without the quotes
- it should answer by the list of available commands and a short explanation
- if you want to know more about a command you can do "!help command"

**Install/uninstall a plugin directly from a git repository**
Try to do::
    !install git@github.com:gbin/err-pollbot.git

You should have instantly a new poll service you can use to vote for where to lunch with you collegues :)

You can imply uninstall a plugin by its name:
!uninstall err-pollbot

**Writing a simple plugin**

Let say you want to make an helloWorld plugin.
Create those files in the "builtins" directory for a quick try,  I will explain below how to correctly package and/or distribute your plugin.

First define a class implementing BotPlugin with a method decorated by @botcmd as follow :

helloWorld.py::
    from botplugin import BotPlugin
    from jabberbot import botcmd

    class HelloWorld(BotPlugin):
        @botcmd
        def hello(self, mess, args):
            """ this command says hello """
            return 'Hello World !'

Then you need to put some metadescription in a .plug file.

helloWorld.plug::
    [Core]
    Name = HelloWorld
    Module = helloWorld

    [Documentation]
    Description = let's say hello !

Start/restart the bot with the command !restart if it has been started with the shell script helper.

That's it !
You can check if the plugin correctly load with the !status command.
Then you can check if the hello command is correcly bound with !help.
Then you can try it : !hello

**Advanced programming tips**

- You can access a preinitialized shelf per plugin with self.shelf (see http://docs.python.org/library/shelve.html)
- You can intercept any message by defining the method callback_message::

    def callback_message(self, conn, mess):
        print "message $s arrived !" % mess

- You can asynchronously send a message (nice to notify the users that a long processing is going on)::

    self.send(mess.getFrom(), "/me is computing ... ", message_type=mess.getType())
    [...] # long processing
    return "Done !"

Feel free to look at the example plugins published for more advance tricks.
