from collections import deque
import inspect
import logging
from pyexpat import ExpatError
from xmpp.simplexml import XML2Node
from errbot import botcmd
import difflib
from errbot.utils import get_sender_username, xhtml2txt
from errbot.templating import tenv
import traceback
from errbot.utils import get_jid_from_message, utf8
from config import BOT_ADMINS, BOT_ASYNC, BOT_PREFIX, \
    BOT_PREFIX_SEPARATORS, ACCESS_CONTROLS
try:
    from config import DIVERT_TO_PRIVATE
except ImportError:
    DIVERT_TO_PRIVATE = ()
    logging.warning("DIVERT_TO_PRIVATE is missing in config")
    pass

if BOT_ASYNC:
    from errbot.bundled.threadpool import ThreadPool, WorkRequest

class Identifier(object):
    """
    This class is the parent and the basic contract of all the ways the backends are identifying a person on their system
    """

    def __init__(self, jid=None, node='', domain='', resource=''):
        if jid:
            if jid.find('@') != -1:
                self.node, self.domain = jid.split('@')[0:2] # hack for IRC
                if self.domain.find('/') != -1:
                    self.domain, self.resource = self.domain.split('/')[0:2] # hack for IRC where you can have several slashes here
                else:
                    self.resource = None
            else:
                self.node = jid
                self.resource = None
                self.domain = None
        else:
            self.node = node
            self.domain = domain
            self.resource = resource

    def getNode(self):
        return self.node

    def getDomain(self):
        return self.domain

    def bareMatch(self, other):
        return other.getStripped() == self.getStripped()

    def getStripped(self):
        if self.domain:
            return self.node + '@' + self.domain
        return self.node # if the backend has no domain notion

    def getResource(self):
        return self.resource

    def __str__(self):
        answer = self.getStripped()
        if self.resource:
            answer += '/' + self.resource
        return answer

    def __unicode__(self):
        return unicode(self.__str__())


class Message(object):
    fr = Identifier('unknown@localhost')

    def __init__(self, body, typ='chat', html=None):
        self.body = body
        self.html = html
        self.typ = typ

    def setTo(self, to):
        if isinstance(to, Identifier):
            self.to = to
        else:
            self.to = Identifier(to) #assume a parseable string

    def getTo(self):
        return self.to

    def setType(self, typ):
        self.typ = typ

    def getType(self):
        return self.typ

    def getFrom(self):
        return self.fr

    def setFrom(self, fr):
        if isinstance(fr, Identifier):
            self.fr = fr
        else:
            self.fr = Identifier(fr) #assume a parseable string

    def getProperties(self):
        return {}

    def getBody(self):
        return self.body

    def getHTML(self):
        return self.html

    # XMPP backward compliance
    def getTagAttr(self, tag, attr):
        return None

    def getTagData(self, tag):
        return None

    def getTag(self, tag):
        return None


class Connection(object):
    def send_message(self, mess):
        raise NotImplementedError("It should be implemented specifically for your backend")


class Backend(object):
    # Implements the basic Bot logic (logic independent from the backend) and leave to you to implement the missing parts

    cmd_history = deque(maxlen=10)
    MSG_ERROR_OCCURRED = 'Sorry for your inconvenience. '\
                         'An unexpected error occurred.'
    MESSAGE_SIZE_LIMIT = 10000 # the default one from hipchat
    MESSAGE_SIZE_ERROR_MESSAGE = '|<- SNIP ! Message too long.'
    MSG_UNKNOWN_COMMAND = 'Unknown command: "%(command)s". '\
                          'Type "' + BOT_PREFIX + 'help" for available commands.'
    MSG_HELP_TAIL = 'Type help <command name> to get more info '\
                    'about that specific command.'
    MSG_HELP_UNDEFINED_COMMAND = 'That command is not defined.'


    def __init__(self, *args, **kwargs):
        """ Those arguments will be directly those put in BOT_IDENTITY
        """
        if BOT_ASYNC:
            self.thread_pool = ThreadPool(3)
            logging.debug('created the thread pool' + str(self.thread_pool))
        self.commands = {} # the dynamically populated list of commands available on the bot

    def build_text_html_message_pair(self, source):
        node = None
        text_plain = None

        try:
            node = XML2Node(utf8(source))
            text_plain = xhtml2txt(source)
        except ExpatError as ee:
            if source.strip(): # avoids keep alive pollution
                logging.debug('Could not parse [%s] as XHTML-IM, assume pure text Parsing error = [%s]' % (source, ee))
                text_plain = source
        return text_plain, node


    def send_message(self, mess):
        """Send a message"""
        self.connect().send_message(mess)

    def send_simple_reply(self, mess, text, private=False):
        """Send a simple response to a message"""
        self.send_message(self.build_reply(mess, text, private))

    def build_reply(self, mess, text=None, private=False):
        """Build a message for responding to another message.
        Message is NOT sent"""
        response = self.build_message(text)
        if private:
            # Use get_jid_from_message here instead of mess.getFrom because
            # getFrom will return the groupchat id instead of user's jid when
            # sent from a chatroom
            response.setTo(get_jid_from_message(mess))
            response.setType('chat')
            response.setFrom(self.jid)
        else:
            response.setTo(mess.getFrom().getStripped())
            response.setType(mess.getType())
            response.setFrom(self.jid)
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

        if not text.startswith(BOT_PREFIX) and type == 'chat':
            text = BOT_PREFIX + text

        if not text.startswith(BOT_PREFIX):
            return True

        text = text[len(BOT_PREFIX):]


        # check to see if any separators exist and strip them out
        for sep in BOT_PREFIX_SEPARATORS:
            if text[:1] == sep:
                text = text[2:]

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

        if command == BOT_PREFIX: # we did "!!" so recall the last command
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
                    logging.exception(u'An error happened while processing '\
                                      u'a message ("%s") from %s: %s"' %
                                      (text, jid, traceback.format_exc(e)))
                    reply = self.MSG_ERROR_OCCURRED + ':\n %s' % e
                if reply:
                    if len(reply) > self.MESSAGE_SIZE_LIMIT:
                        reply = reply[:self.MESSAGE_SIZE_LIMIT - len(self.MESSAGE_SIZE_ERROR_MESSAGE)] + self.MESSAGE_SIZE_ERROR_MESSAGE
                    self.send_simple_reply(mess, reply, cmd in DIVERT_TO_PRIVATE)

            # Check access controls
            usr = get_jid_from_message(mess)
            typ = mess.getType()
            if cmd in ACCESS_CONTROLS:
                if 'allowusers' in ACCESS_CONTROLS[cmd]:
                    if usr not in ACCESS_CONTROLS[cmd]['allowusers']:
                        self.send_simple_reply(mess, "You're not allowed to access this command from this user")
                        return False
                if 'denyusers' in ACCESS_CONTROLS[cmd]:
                    if usr in ACCESS_CONTROLS[cmd]['denyusers']:
                        self.send_simple_reply(mess, "You're not allowed to access this command from this user")
                        return False
                if typ == 'groupchat':
                    stripped = mess.getFrom().getStripped()
                    if 'allowmuc' in ACCESS_CONTROLS[cmd] and ACCESS_CONTROLS[cmd]['allowmuc'] is False:
                        self.send_simple_reply(mess, "You're not allowed to access this command from a chatroom")
                        return False
                    if 'allowrooms' in ACCESS_CONTROLS[cmd] and stripped not in ACCESS_CONTROLS[cmd]['allowrooms']:
                            self.send_simple_reply(mess, "You're not allowed to access this command from this room")
                            return False
                    if 'denyrooms' in ACCESS_CONTROLS[cmd] and stripped in ACCESS_CONTROLS[cmd]['denyrooms']:
                        self.send_simple_reply(mess, "You're not allowed to access this command from this room")
                        return False
                else:
                    if 'allowprivate' in ACCESS_CONTROLS[cmd] and ACCESS_CONTROLS[cmd]['allowprivate'] is False:
                        self.send_simple_reply(mess, "You're not allowed to access this command via private message to me")
                        return False

            f = self.commands[cmd]

            if f._err_command_admin_only:
                if typ == 'groupchat':
                    self.send_simple_reply(mess, 'You cannot administer the bot from a chatroom, message the bot directly')
                    return False
                if usr not in BOT_ADMINS:
                    self.send_simple_reply(mess, 'You cannot administer the bot from this user %s.' % usr)
                    return False
                if BOT_ASYNC:
                    self.thread_pool.wait() # If it is an admin command, wait that the queue is completely depleted so we don't have strange concurrency issues on load/unload/updates etc ...

            if f._err_command_historize:
                self.cmd_history.append((cmd, args)) # add it to the history only if it is authorized to be so

            # Don't check for None here as None can be a valid argument to split.
            # '' was chosen as default argument because this isn't a valid argument to split()
            if f._err_command_split_args_with != '':
                args = args.split(f._err_command_split_args_with)
            if BOT_ASYNC:
                wr = WorkRequest(execute_and_send, [f._err_command_template]) #execute_and_send(f._err_command_template)
                self.thread_pool.putRequest(wr)
                if f._err_command_admin_only:
                    self.thread_pool.wait() # Again wait for the completion before accepting a new command that could generate weird concurrency issues
            else:
                execute_and_send(f._err_command_template)

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
        if len(BOT_PREFIX) > 1:
            local_prefix = BOT_PREFIX + ' '
        else:
            local_prefix = BOT_PREFIX

        if full_cmd:
            part1 = 'Command "%s" / "%s" not found.' % (cmd, full_cmd)
        else:
            part1 = 'Command "%s" not found.' % cmd
        ununderscore_keys = [m.replace('_', ' ') for m in self.commands.keys()]
        matches = difflib.get_close_matches(cmd, ununderscore_keys)
        if full_cmd:
            matches.extend(difflib.get_close_matches(full_cmd, ununderscore_keys))
        matches = set(matches)
        if matches:
            return part1 + '\n\nDid you mean "' + local_prefix + ('" or "' +
                                       local_prefix).join(matches) + '" ?'
        else:
            return part1

    def inject_commands_from(self, instance_to_inject):
        classname = instance_to_inject.__class__.__name__
        for name, value in inspect.getmembers(instance_to_inject, inspect.ismethod):
            if getattr(value, '_err_command', False):
                name = getattr(value, '_err_command_name')

                if name in self.commands:
                    f = self.commands[name]
                    new_name = (classname + '-' + name).lower()
                    self.warn_admins('%s.%s clashes with %s.%s so it has been renamed %s' % (classname, name, f.im_class.__name__, f.__name__, new_name ))
                    name = new_name
                logging.debug('Adding command : %s -> %s' % (name, value.__name__))
                self.commands[name] = value

    def remove_commands_from(self, instance_to_inject):
        for name, value in inspect.getmembers(instance_to_inject, inspect.ismethod):
            if getattr(value, '_err_command', False):
                name = getattr(value, '_err_command_name')
                del(self.commands[name])

    def warn_admins(self, warning):
        for admin in BOT_ADMINS:
            self.send(admin, warning)

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

            logging.info("help here")
            if len(BOT_PREFIX) > 1:
                print "here"
                local_prefix = '%s ' % BOT_PREFIX
            else:
                print "nothere"
                local_prefix = BOT_PREFIX
            usage = '\n'.join(sorted([
            local_bot_prefix + '%s: %s' % (name, (command.__doc__ or
                                '(undocumented)').strip().split('\n', 1)[0])
            for (name, command) in self.commands.iteritems()\
            if name != 'help'\
            and not command._err_command_hidden
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

    def send(self, user, text, in_reply_to=None, message_type='chat'):
        """Sends a simple message to the specified user."""
        mess = self.build_message(text)
        if isinstance(user, basestring):
            mess.setTo(user)
        else:
            mess.setTo(user.getStripped())

        if in_reply_to:
            mess.setType(in_reply_to.getType())
            mess.setFrom(in_reply_to.getTo().getStripped())
        else:
            mess.setType(message_type)
            mess.setFrom(self.jid)

        self.send_message(mess)


    ###### HERE ARE THE SPECIFICS TO IMPLEMENT PER BACKEND

    def build_message(self, text):
        raise NotImplementedError("It should be implemented specifically for your backend")

    def serve_forever(self):
        raise NotImplementedError("It should be implemented specifically for your backend")

    def connect(self):
        """Connects the bot to server or returns current connection
        """
        raise NotImplementedError("It should be implemented specifically for your backend")

    def join_room(self, room, username=None, password=None):
        raise NotImplementedError("It should be implemented specifically for your backend")

    def shutdown(self):
        pass

    def connect_callback(self):
        pass

    def disconnect_callback(self):
        pass

    @property
    def mode(self):
        raise NotImplementedError("It should be implemented specifically for your backend")
