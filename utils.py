# -*- coding: utf-8 -*-
import logging
import inspect
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

    jid = str(mess.getFrom()).split('/')[1]

    logging.debug('deduced the jid from the chatroom from %s' % jid)
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
        value_in_chr = int(round((value * BAR_WIDTH / max) ))
    else:
        value_in_chr = 0
        
    return u'[' + u'█' * value_in_chr + u'▒' * int(round(BAR_WIDTH - value_in_chr)) + u']'


# Introspect to know from which plugin a command is implemented
def get_class_for_method(meth):
  for cls in inspect.getmro(meth.im_class):
    if meth.__name__ in cls.__dict__: return cls
  return None
