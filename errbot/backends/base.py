from collections import deque
import inspect
import logging
import thread
from errbot import botcmd
import difflib
from errbot.utils import get_sender_username
from errbot.templating import tenv
import traceback
from errbot.utils import get_jid_from_message
from config import BOT_ADMINS

class Identifier(object):
    """
    This class is the parent and the basic contract of all the ways the backends are identifying a person on their system
    """
    def __init__(self, jid=None, node='', domain='', resource=''):
        self.node = node
    def getNode(self):
        return self.node
    def bareMatch(self, other):
        return other.node == self.node
    def getStripped(self):
        return self.node

class Message(object):
    typ = 'chat'
    fr = Identifier('mock')
    def __init__(self, body, html = None):
        self.body = body
        self.html = html

    def setTo(self, to):
        self.to = to

    def setType(self, typ):
        self.typ = typ

    def getType(self):
        return self.typ

    def getFrom(self):
        return self.fr

    def setFrom(self, fr):
        self.fr = fr

    def getProperties(self):
        return {}

    def getBody(self):
        return self.body

    def getHTML(self):
        return self.html

    def getThread(self):
        return None

    def setThread(self, thread):
        return None

class Connection(object):
    def send(self, mess):
        raise NotImplementedError( "It should be implemented specifically for your backend" )

class Backend(object):
    """
        Implements the basic Bot logic (logic independent from the backend) and leave to you to implement the missing parts
    """

    cmd_history = deque(maxlen=10)
    MSG_ERROR_OCCURRED = 'Sorry for your inconvenience. '\
                         'An unexpected error occurred.'
    MESSAGE_SIZE_LIMIT = 10000 # the default one from hipchat
    MESSAGE_SIZE_ERROR_MESSAGE = '|<- SNIP ! Message too long.'
    MSG_UNKNOWN_COMMAND = 'Unknown command: "%(command)s". '\
                          'Type "!help" for available commands.'
    MSG_HELP_TAIL = 'Type help <command name> to get more info '\
                    'about that specific command.'
    MSG_HELP_UNDEFINED_COMMAND = 'That command is not defined.'


    def __init__(self, *args, **kwargs):
        """ Those arguments will be directly those put in BOT_IDENTITY
        """
        self.refresh_command_list()

    def refresh_command_list(self):
        self.commands = {}
        for name, value in inspect.getmembers(self, inspect.ismethod):
            if getattr(value, '_jabberbot_command', False):
                name = getattr(value, '_jabberbot_command_name')
                logging.info('Registered command: %s' % name)
                self.commands[name] = value


    def send_message(self, mess):
        """Send a message"""
        self.connect().send(mess)

    def send_simple_reply(self, mess, text, private=False):
        """Send a simple response to a message"""
        self.send_message(self.build_reply(mess, text, private))

    def build_reply(self, mess, text=None, private=False):
        """Build a message for responding to another message.
        Message is NOT sent"""
        response = self.build_message(text)
        if private:
            response.setTo(mess.getFrom())
            response.setType('chat')
        else:
            response.setTo(mess.getFrom().getStripped())
            response.setType(mess.getType())
        response.setThread(mess.getThread())
        return response

    def callback_message(self, conn, mess):
        """
        Needs to return False if we want to stop further treatment
        """
        # Prepare to handle either private chats or group chats
        type = mess.getType()
        jid = mess.getFrom()
        props = mess.getProperties()
        text = mess.getBody()
        username = get_sender_username(mess)

        if type not in ("groupchat", "chat"):
            logging.debug("unhandled message type %s" % mess)
            return False

        logging.debug("*** props = %s" % props)
        logging.debug("*** jid = %s" % jid)
        logging.debug("*** username = %s" % username)
        logging.debug("*** type = %s" % type)
        logging.debug("*** text = %s" % text)

        # If a message format is not supported (eg. encrypted),
        # txt will be None
        if not text: return False

        if not text.startswith('!'):
            return True

        text = text[1:]
        text_split = text.strip().split(' ')

        cmd = None
        command = None
        args = ''
        if len(text_split) > 1:
            command = (text_split[0] + '_' + text_split[1]).lower()
            if self.commands.has_key(command):
                cmd = command
                args = ' '.join(text_split[2:])

        if not cmd:
            command = text_split[0].lower()
            args = ' '.join(text_split[1:])
            if self.commands.has_key(command):
                cmd = command
                if len(text_split) > 1:
                    args = ' '.join(text_split[1:])

        if command == '!': # we did "!!" so recall the last command
            if len(self.cmd_history):
                cmd, args = self.cmd_history[-1]
            else:
                return False # no command in history
        elif command.isdigit(): # we did "!#" so we recall the specified command
            index = int(command)
            if len(self.cmd_history) >= index:
                cmd, args = self.cmd_history[-index]
            else:
                return False # no command in history

        if (cmd, args) in self.cmd_history:
            self.cmd_history.remove((cmd, args)) # we readd it below

        logging.info("received command = %s matching [%s] with parameters [%s]" % (command, cmd, args))

        if cmd:
            def execute_and_send(template_name):
                try:
                    reply = self.commands[cmd](mess, args)

                    # integrated templating
                    if template_name:
                        reply = tenv().get_template(template_name + '.html').render(**reply)

                except Exception, e:
                    logging.exception('An error happened while processing '\
                                       'a message ("%s") from %s: %s"' %
                                       (text, jid, traceback.format_exc(e)))
                    reply = self.MSG_ERROR_OCCURRED + ':\n %s' % e
                if reply:
                    if len(reply) > self.MESSAGE_SIZE_LIMIT:
                        reply = reply[:self.MESSAGE_SIZE_LIMIT - len(self.MESSAGE_SIZE_ERROR_MESSAGE)] + self.MESSAGE_SIZE_ERROR_MESSAGE
                    self.send_simple_reply(mess, reply)

            f = self.commands[cmd]

            if f._jabberbot_command_admin_only:
                if mess.getType() == 'groupchat':
                    self.send_simple_reply(mess, 'You cannot administer the bot from a chatroom, message the bot directly')
                    return False
                usr = get_jid_from_message(mess)
                if usr not in BOT_ADMINS:
                    self.send_simple_reply(mess, 'You cannot administer the bot from this user %s.' % usr)
                    return False

            if f._jabberbot_command_historize:
                self.cmd_history.append((cmd,  args)) # add it to the history only if it is authorized to be so

            if f._jabberbot_command_split_args_with:
                args = args.split(f._jabberbot_command_split_args_with)

            # Experimental!
            # if command should be executed in a seperate thread do it
            if f._jabberbot_command_thread:
                thread.start_new_thread(execute_and_send, (f._jabberbot_command_template,))
            else:
                execute_and_send(f._jabberbot_command_template)
        else:
            # In private chat, it's okay for the bot to always respond.
            # In group chat, the bot should silently ignore commands it
            # doesn't understand or aren't handled by unknown_command().
            reply = self.unknown_command(mess, command, args)
            if reply is None:
                reply = self.MSG_UNKNOWN_COMMAND % {'command': command}
            if reply:
                self.send_simple_reply(mess, reply)

        return True

    def unknown_command(self, mess, cmd, args):
        """ Override the default unknown command behavior
        """
        full_cmd = cmd + ' ' + args.split(' ')[0] if args else None
        if full_cmd:
            part1 = 'Command "%s" / "%s" not found.' % (cmd, full_cmd)
        else:
            part1 = 'Command "%s" not found.' % cmd
        ununderscore_keys = [m.replace('_',' ') for m in self.commands.keys()]
        matches = difflib.get_close_matches(cmd, ununderscore_keys)
        if full_cmd:
            matches.extend(difflib.get_close_matches(full_cmd, ununderscore_keys))
        matches = set(matches)
        if matches:
            return part1 + '\n\nDid you mean "!' + '" or "!'.join(matches) + '" ?'
        else:
            return part1

    def top_of_help_message(self):
        """Returns a string that forms the top of the help message

        Override this method in derived class if you
        want to add additional help text at the
        beginning of the help message.
        """
        return ""

    def bottom_of_help_message(self):
        """Returns a string that forms the bottom of the help message

        Override this method in derived class if you
        want to add additional help text at the end
        of the help message.
        """
        return ""

    @botcmd
    def help(self, mess, args):
        """   Returns a help string listing available options.

        Automatically assigned to the "help" command."""
        if not args:
            if self.__doc__:
                description = self.__doc__.strip()
            else:
                description = 'Available commands:'

            usage = '\n'.join(sorted([
            '!%s: %s' % (name, (command.__doc__ or
                                '(undocumented)').strip().split('\n', 1)[0])
            for (name, command) in self.commands.iteritems()\
            if name != 'help'\
            and not command._jabberbot_command_hidden
            ]))
            usage = '\n\n' + '\n\n'.join(filter(None, [usage, self.MSG_HELP_TAIL]))
        else:
            description = ''
            if args in self.commands:
                usage = (self.commands[args].__doc__ or
                         'undocumented').strip()
            else:
                usage = self.MSG_HELP_UNDEFINED_COMMAND

        top = self.top_of_help_message()
        bottom = self.bottom_of_help_message()
        return ''.join(filter(None, [top, description, usage, bottom]))

    @botcmd(historize = False)
    def history(self, mess, args):
        """display the command history"""
        answer = []
        l = len(self.cmd_history)
        for i in range(0, l):
            c = self.cmd_history[i]
            answer.append('%2i:!%s %s' %(l-i,c[0],c[1]))
        return '\n'.join(answer)

    ###### HERE ARE THE SPECIFICS TO IMPLEMENT PER BACKEND

    def build_message(self, text):
        raise NotImplementedError( "It should be implemented specifically for your backend" )

    def serve_forever(self, connect_callback=None, disconnect_callback=None):
        raise NotImplementedError( "It should be implemented specifically for your backend" )

    def connect(self):
        """Connects the bot to server or returns current connection
        """
        raise NotImplementedError( "It should be implemented specifically for your backend" )

    def join_room(self, room, username=None, password=None):
        raise NotImplementedError( "It should be implemented specifically for your backend" )

    def shutdown(self):
        pass

    def connect_callback(self):
        pass

    def disconnect_callback(self):
        pass


