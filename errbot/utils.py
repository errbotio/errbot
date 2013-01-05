# -*- coding: utf-8 -*-
import logging
import inspect
import os
import re
from html import entities
import sys
import time

PY3 = sys.version_info[0] == 3
PY2 = not PY3

PLUGINS_SUBDIR = b'plugins' if PY2 else 'plugins'


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

    if PY2 and to_check_type.__name__ == 'str':  # __name__ to avoid beeing touched by 3to2
        to_check_type = unicode
        to_check = to_check.decode()

    # Skip this check if the sample is None because it will always be something
    # other than NoneType when changed from the default. Raising ValidationException
    # would make no sense then because it would defeat the whole purpose of having
    # that key in the sample when it could only ever be None.
    if sample is not None and sample_type != to_check_type:
        raise ValidationException('%s [%s] is not the same type as %s [%s]' % (sample, sample_type, to_check, to_check_type))

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
        text = m.group(0)
        if text[:2] == "&#":
            # character reference
            try:
                if text[:3] == "&#x":
                    return chr(int(text[3:-1], 16))
                else:
                    return chr(int(text[2:-1]))
            except ValueError:
                pass
        else:
            # named entity
            try:
                text = chr(entities.name2codepoint[text[1:-1]])
            except KeyError:
                pass
        return text  # leave as is

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
    if hasattr(mess, 'getHTML'):  # somebackends are happy to give you the HTML
        html_content = mess.getHTML()
    else:
        html_content = mess.getTag('html')

    if html_content:
        body = html_content.getTag('body')
        return ''.join([str(kid) for kid in body.kids]) + body.getData(), True
    else:
        return mess.getBody(), False


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