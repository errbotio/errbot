# -*- coding: utf-8 -*-
import logging
import inspect
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


def which(program):
    def is_exe(fpath):
        return os.path.isfile(fpath) and os.access(fpath, os.X_OK)

    fpath, fname = os.path.split(program)
    if fpath:
        if is_exe(program):
            return program
    else:
        for path in os.environ["PATH"].split(os.pathsep):
            exe_file = os.path.join(path, program)
            if is_exe(exe_file):
                return exe_file

    return None


def version2array(version):
    response = [int(el) for el in version.split('.')]
    if len(response) != 3:
        raise Exception('version %s in not in format "x.y.z" for example "1.2.2"' % version)
    return response


class ValidationException(Exception):
    pass


def recurse_check_structure(sample, to_check):
    sample_type = type(sample)
    to_check_type = type(to_check)
    if sample_type != to_check_type:
        raise ValidationException('%s [%s] is not the same type as %s [%s]' % (sample, sample_type, to_check_type, to_check_type))

    if sample_type in (list, tuple):
        for element in to_check:
            recurse_check_structure(sample[0], element)
        return

    if sample_type == dict:
        for key in sample:
            if not to_check.has_key(key):
                raise ValidationException("%s doesn't contain the key %s" % (to_check, key))
        for key in to_check:
            if not sample.has_key(key):
                raise ValidationException("%s contains an unknown key %s" % (to_check, key))
        for key in sample:
            recurse_check_structure(sample[key], to_check[key])
        return
import re, htmlentitydefs

##
# Removes HTML or XML character references and entities from a text string.
#
# @param text The HTML (or XML) source text.
# @return The plain text, as a Unicode string, if necessary.

def unescape_xml(text):
    def fixup(m):
        text = m.group(0)
        if text[:2] == "&#":
            # character reference
            try:
                if text[:3] == "&#x":
                    return unichr(int(text[3:-1], 16))
                else:
                    return unichr(int(text[2:-1]))
            except ValueError:
                pass
        else:
            # named entity
            try:
                text = unichr(htmlentitydefs.name2codepoint[text[1:-1]])
            except KeyError:
                pass
        return text # leave as is
    return re.sub("&#?\w+;", fixup, text)

REMOVE_EOL = re.compile(r'\n')
REINSERT_EOLS = re.compile(r'</p>|</li>|<br/>', re.I)
ZAP_TAGS = re.compile(r'<[^>]+>')

def xhtml2txt(xhtml):
    text_plain = REMOVE_EOL.sub('', xhtml) # Ignore formatting TODO exclude pre
    text_plain = REINSERT_EOLS.sub('\n', text_plain) # readd the \n where they probably fit best
    text_plain = ZAP_TAGS.sub('', text_plain) # zap every tag left
    return unescape_xml(text_plain).strip()


HIPCHAT_FORCE_PRE = re.compile(r'<body>', re.I)
HIPCHAT_FORCE_SLASH_PRE = re.compile(r'</body>', re.I)
HIPCHAT_EOLS = re.compile(r'</p>|</li>', re.I)
HIPCHAT_BOLS = re.compile(r'<p [^>]+>|<li [^>]+>', re.I)

# Hipchat has a really limited html support
def xhtml2hipchat(xhtml):
    retarded_hipchat_html_plain = REMOVE_EOL.sub('', xhtml) # Ignore formatting
    retarded_hipchat_html_plain = HIPCHAT_EOLS.sub('<br/>', retarded_hipchat_html_plain) # readd the \n where they probably fit best
    retarded_hipchat_html_plain = HIPCHAT_BOLS.sub('', retarded_hipchat_html_plain) # zap every tag left
    retarded_hipchat_html_plain = HIPCHAT_FORCE_PRE.sub('<body><pre>', retarded_hipchat_html_plain) # fixor pre
    retarded_hipchat_html_plain = HIPCHAT_FORCE_SLASH_PRE.sub('</pre></body>', retarded_hipchat_html_plain) # fixor /pre
    return retarded_hipchat_html_plain


def unicode_filter(key):
    if type(key) == unicode:
        return key.encode('utf-8')
    return key

def mess_2_embeddablehtml(mess):
    html_content = mess.getHTML()

    if html_content:
        body = html_content.getTag('body')
        return ''.join([unicode(kid) for kid in body.kids]) + body.getData(), True
    else:
        return mess.getBody(), False
