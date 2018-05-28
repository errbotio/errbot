# -*- coding: utf-8 -*-
import fnmatch
import inspect
import logging
import os
import re
import sys
import time
from platform import system
from functools import wraps
from html import entities

log = logging.getLogger(__name__)

ON_WINDOWS = system() == 'Windows'

PLUGINS_SUBDIR = 'plugins'


# noinspection PyPep8Naming
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


# Introspect to know from which plugin a command is implemented
def get_class_for_method(meth):
    for cls in inspect.getmro(type(meth.__self__)):
        if meth.__name__ in cls.__dict__:
            return cls
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

    return re.sub(r'&#?\w+;', fixup, text)


REMOVE_EOL = re.compile(r'\n')
REINSERT_EOLS = re.compile(r'</p>|</li>|<br/>', re.I)
ZAP_TAGS = re.compile(r'<[^>]+>')


def rate_limited(min_interval):
    """
    decorator to rate limit a function.

    :param min_interval: minimum interval allowed between 2 consecutive calls.
    :return: the decorated function
    """
    def decorate(func):
        last_time_called = [0.0]

        def rate_limited_function(*args, **kargs):
            elapsed = time.time() - last_time_called[0]
            log.debug('Elapsed %f since last call' % elapsed)
            left_to_wait = min_interval - elapsed
            if left_to_wait > 0:
                log.debug('Wait %f due to rate limiting...' % left_to_wait)
                time.sleep(left_to_wait)
            ret = func(*args, **kargs)
            last_time_called[0] = time.time()
            return ret

        return rate_limited_function

    return decorate


def split_string_after(str_, n):
    """Yield chunks of length `n` from the given string

    :param n: length of the chunks.
    :param str_: the given string.
    """
    for start in range(0, max(len(str_), 1), n):
        yield str_[start:start + n]


def find_roots(path, file_sig='*.plug'):
    """Collects all the paths from path recursively that contains files of type `file_sig`.

       :param path:
            a base path to walk from
       :param file_sig:
            the file pattern to look for
       :return: a set of paths
    """
    roots = set()  # you can have several .plug per directory.
    for root, dirnames, filenames in os.walk(path, followlinks=True):
        for filename in fnmatch.filter(filenames, file_sig):
            dir_to_add = os.path.dirname(os.path.join(root, filename))
            relative = os.path.relpath(os.path.realpath(dir_to_add), os.path.realpath(path))
            for subelement in relative.split(os.path.sep):
                # if one of the element is just a relative construct, it is ok to continue inspecting it.
                if subelement in ('.', '..'):
                    continue
                # if it is an hidden directory or a python temp directory, just ignore it.
                if subelement.startswith('.') or subelement == '__pycache__':
                    log.debug("Ignore %s" % dir_to_add)
                    break
            else:
                roots.add(dir_to_add)
    return roots


def collect_roots(base_paths, file_sig='*.plug'):
    """Collects all the paths from base_paths recursively that contains files of type `file_sig`.

       :param base_paths:
            a list of base paths to walk from
            elements can be a string or a list/tuple of strings

       :param file_sig:
            the file pattern to look for
       :return: a set of paths
    """
    result = set()
    for path_or_list in base_paths:
        if isinstance(path_or_list, (list, tuple)):
            result |= collect_roots(base_paths=path_or_list, file_sig=file_sig)
        elif path_or_list is not None:
            result |= find_roots(path_or_list, file_sig)
    return result


def global_restart():
    """Restart the current process."""
    python = sys.executable
    os.execl(python, python, *sys.argv)
