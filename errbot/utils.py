# -*- coding: utf-8 -*-
import logging
import inspect
import fcntl
import os

PLUGINS_SUBDIR = 'plugins'

def get_sender_username(mess):
    """Extract the sender's user name from a message"""
    type = mess.getType()
    jid = mess.getFrom()
    if type == "groupchat":
        username = jid.getResource()
    elif type == "chat":
        username = jid.getNode()
    else:
        username = ""
    return username


def get_jid_from_message(mess):
    if mess.getType() == 'chat':
        return str(mess.getFrom().getStripped())
        # this is a hipchat message from a group so find out from the sender node, for the moment hardcoded because it is not parsed, it could brake in the future
    jid = mess.getTagAttr('delay', 'from_jid')
    if jid:
        logging.debug('found the jid from the delay tag : %s' % jid)
        return jid
    jid = mess.getTagData('sender')
    if jid:
        logging.debug('found the jid from the sender tag : %s' % jid)
        return jid
    x = mess.getTag('x')
    if x:
        jid = x.getTagData('sender')

    if jid:
        logging.debug('found the jid from the x/sender tag : %s' % jid)
        return jid
    splitted = str(mess.getFrom()).split('/')
    jid = splitted[1] if len(splitted) > 1 else splitted[0] # despair

    logging.debug('deduced the jid from the chatroom to %s' % jid)
    return jid


def format_timedelta(timedelta):
    total_seconds = timedelta.seconds + (86400 * timedelta.days)
    hours, remainder = divmod(total_seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    if hours == 0 and minutes == 0:
        return '%i seconds' % seconds
    elif not hours:
        return '%i minutes' % minutes
    elif not minutes:
        return '%i hours' % hours
    else:
        return '%i hours and %i minutes' % (hours, minutes)

BAR_WIDTH = 15.0

def drawbar(value, max):
    if max:
        value_in_chr = int(round((value * BAR_WIDTH / max)))
    else:
        value_in_chr = 0
    return u'[' + u'█' * value_in_chr + u'▒' * int(round(BAR_WIDTH - value_in_chr)) + u']'


# Introspect to know from which plugin a command is implemented
def get_class_for_method(meth):
    for cls in inspect.getmro(meth.im_class):
        if meth.__name__ in cls.__dict__: return cls
    return None


def human_name_for_git_url(url):
    # try to humanize the last part of the git url as much as we can
    if url.find('/') > 0:
        s = url.split('/')
    else:
        s = url.split(':')
    last_part = str(s[-1]) if s[-1] else str(s[-2])
    return last_part[:-4] if last_part.endswith('.git') else last_part


def tail( f, window=20 ):
    return ''.join(f.readlines()[-window:])


class PidFile(object):
    """Context manager that locks a pid file.  Implemented as class
    not generator because daemon.py is calling .__exit__() with no parameters
    instead of the None, None, None specified by PEP-343."""
    # pylint: disable=R0903

    def __init__(self, path):
        self.path = path
        self.pidfile = None

    def __enter__(self):
        self.pidfile = open(self.path, "a+")
        try:
            fcntl.flock(self.pidfile.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except IOError:
            raise SystemExit("Already running according to " + self.path)
        self.pidfile.seek(0)
        self.pidfile.truncate()
        self.pidfile.write(str(os.getpid()))
        self.pidfile.flush()
        self.pidfile.seek(0)
        return self.pidfile

    def __exit__(self, exc_type=None, exc_value=None, exc_tb=None):
        try:
            self.pidfile.close()
        except IOError as err:
            # ok if file was just closed elsewhere
            if err.errno != 9:
                raise
        os.remove(self.path)