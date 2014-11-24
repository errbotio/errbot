# -*- coding: utf-8 -*-
from itertools import starmap, repeat
import logging
import os
import re
from html import entities
import sys
import time
from functools import wraps
from xml.etree.ElementTree import tostring
import inspect


PY3 = sys.version_info[0] == 3
PY2 = not PY3

PLUGINS_SUBDIR = b'plugins' if PY2 else 'plugins'


def get_sender_username(mess):
    """Extract the sender's user name from a message"""
    type_ = mess.type
    jid = mess.frm
    if type_ == "groupchat":
        username = jid.resource
    elif type_ == "chat":
        username = jid.node
    else:
        username = ""
    return username


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
    return '[' + '█' * value_in_chr + '▒' * int(round(BAR_WIDTH - value_in_chr)) + ']'


# Introspect to know from which plugin a command is implemented
def get_class_for_method(meth):
    for cls in inspect.getmro(type(meth.__self__)):
        if meth.__name__ in cls.__dict__:
            return cls
    return None


def human_name_for_git_url(url):
    # try to humanize the last part of the git url as much as we can
    if url.find('/') > 0:
        s = url.split('/')
    else:
        s = url.split(':')
    last_part = str(s[-1]) if s[-1] else str(s[-2])
    return last_part[:-4] if last_part.endswith('.git') else last_part


def tail(f, window=20):
    return ''.join(f.readlines()[-window:])


def which(program):
    def is_exe(file_path):
        return os.path.isfile(file_path) and os.access(file_path, os.X_OK)

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


INVALID_VERSION_EXCEPTION = 'version %s in not in format "x.y.z" or "x.y.z-{beta,alpha,rc1,rc2...}" for example "1.2.2"'


def version2array(version):
    vsplit = version.split('-')

    if len(vsplit) == 2:
        main, sub = vsplit
        if sub == 'alpha':
            sub_int = -1
        elif sub == 'beta':
            sub_int = 0
        elif sub.startswith('rc'):
            sub_int = int(sub[2:])
        else:
            raise ValueError(INVALID_VERSION_EXCEPTION % version)

    elif len(vsplit) == 1:
        main = vsplit[0]
        sub_int = sys.maxsize
    else:
        raise ValueError(INVALID_VERSION_EXCEPTION % version)

    response = [int(el) for el in main.split('.')]
    response.append(sub_int)

    if len(response) != 4:
        raise ValueError(INVALID_VERSION_EXCEPTION % version)

    return response


class ValidationException(Exception):
    pass


def recurse_check_structure(sample, to_check):
    sample_type = type(sample)
    to_check_type = type(to_check)

    if PY2 and to_check_type.__name__ == 'str':  # __name__ to avoid beeing touched by 3to2
        # noinspection PyUnresolvedReferences
        to_check_type = unicode
        to_check = to_check.decode()

    # Skip this check if the sample is None because it will always be something
    # other than NoneType when changed from the default. Raising ValidationException
    # would make no sense then because it would defeat the whole purpose of having
    # that key in the sample when it could only ever be None.
    if sample is not None and sample_type != to_check_type:
        raise ValidationException(
            '%s [%s] is not the same type as %s [%s]' % (sample, sample_type, to_check, to_check_type))

    if sample_type in (list, tuple):
        for element in to_check:
            recurse_check_structure(sample[0], element)
        return

    if sample_type == dict:
        for key in sample:
            if key not in to_check:
                raise ValidationException("%s doesn't contain the key %s" % (to_check, key))
        for key in to_check:
            if key not in sample:
                raise ValidationException("%s contains an unknown key %s" % (to_check, key))
        for key in sample:
            recurse_check_structure(sample[key], to_check[key])
        return


def unescape_xml(text):
    """
    Removes HTML or XML character references and entities from a text string.
    @param text The HTML (or XML) source text.
    @return The plain text, as a Unicode string, if necessary.
    """

    def fixup(m):
        txt = m.group(0)
        if txt[:2] == "&#":
            # character reference
            try:
                if txt[:3] == "&#x":
                    return chr(int(txt[3:-1], 16))
                else:
                    return chr(int(txt[2:-1]))
            except ValueError:
                pass
        else:
            # named entity
            try:
                txt = chr(entities.name2codepoint[txt[1:-1]])
            except KeyError:
                pass
        return txt  # leave as is

    return re.sub("&#?\w+;", fixup, text)


REMOVE_EOL = re.compile(r'\n')
REINSERT_EOLS = re.compile(r'</p>|</li>|<br/>', re.I)
ZAP_TAGS = re.compile(r'<[^>]+>')


def xhtml2txt(xhtml):
    text_plain = REMOVE_EOL.sub('', xhtml)  # Ignore formatting TODO exclude pre
    text_plain = REINSERT_EOLS.sub('\n', text_plain)  # readd the \n where they probably fit best
    text_plain = ZAP_TAGS.sub('', text_plain)  # zap every tag left
    return unescape_xml(text_plain).strip()


def utf8(key):
    if type(key) == str:
        return key.encode()  # it defaults to utf-8
    return key


def mess_2_embeddablehtml(mess):
    html_content = mess.html
    if html_content is not None:
        body = html_content.find('{http://jabber.org/protocol/xhtml-im}body')
        result = ''
        for child in body.getchildren():
            result += tostring(child).decode().replace('ns0:', '')
        return result, True
    else:
        return mess.body, False


def parse_jid(jid):
    if jid.find('@') != -1:
        split_jid = jid.split('@')
        node, domain = '@'.join(split_jid[:-1]), split_jid[-1]
        if domain.find('/') != -1:
            domain, resource = domain.split('/')[0:2]  # hack for IRC where you can have several slashes here
        else:
            resource = None
    else:
        node = jid
        domain = None
        resource = None

    return node, domain, resource


def RateLimited(minInterval):
    def decorate(func):
        lastTimeCalled = [0.0]

        def rateLimitedFunction(*args, **kargs):
            elapsed = time.time() - lastTimeCalled[0]
            logging.debug('Elapsed %f since last call' % elapsed)
            leftToWait = minInterval - elapsed
            if leftToWait > 0:
                logging.debug('Wait %f due to rate limiting...' % leftToWait)
                time.sleep(leftToWait)
            ret = func(*args, **kargs)
            lastTimeCalled[0] = time.time()
            return ret

        return rateLimitedFunction

    return decorate


def split_string_after(str_, n):
    """Yield chunks of length `n` from the given string"""
    for start in range(0, len(str_), n):
        yield str_[start:start + n]


class deprecated(object):
    """ deprecated decorator. emits a warning on a call on an old method and call the new method anyway """
    def __init__(self, new=None):
        self.new = new

    def __call__(self, old):
        @wraps(old)
        def wrapper(*args, **kwds):
            msg = ' {0.filename}:{0.lineno} : '.format(inspect.getframeinfo(inspect.currentframe().f_back))
            if len(args):
                pref = type(args[0]).__name__ + '.'  # TODO might break for individual methods
            else:
                pref = ''
            msg += 'call to the deprecated %s%s' % (pref, old.__name__)
            if self.new is not None:
                if type(self.new) is property:
                    msg += '... use the property %s%s instead' % (pref, self.new.fget.__name__)
                else:
                    msg += '... use %s%s instead' % (pref, self.new.__name__)
            msg += '.'
            logging.warning(msg)

            if self.new:
                if type(self.new) is property:
                    return self.new.fget(*args, **kwds)
                return self.new(*args, **kwds)
            return old(*args, **kwds)

        wrapper.__name__ = old.__name__
        wrapper.__doc__ = old.__doc__
        wrapper.__dict__.update(old.__dict__)
        return wrapper

# From the itertools receipes
def repeatfunc(func, times=None, *args):
    """Repeat calls to func with specified arguments.

    Example:  repeatfunc(random.random)
    """
    if times is None:
        return starmap(func, repeat(args))
    return starmap(func, repeat(args, times))