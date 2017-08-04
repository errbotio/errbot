# vim: noai:ts=4:sw=4
import re

from markdown import Markdown
from markdown.extensions.extra import ExtraExtension

# Attribute regexp looks for extendend syntax: {: ... }
ATTR_RE = re.compile(r'{:([^}]*)}')
MD_ESCAPE_RE = re.compile('|'.join(re.escape(c) for c in ('\\', '`', '*', '_', '{', '}', '[', ']',
                                                          '(', ')', '>', '#', '+', '-', '.', '!')))

# Here are few helpers to simplify the conversion from markdown to various
# backend formats.


def ansi():
    """This makes a converter from markdown to ansi (console) format.
    It can be called like this:
    from errbot.rendering import ansi
    md_converter = ansi()  # you need to cache the converter

    ansi_txt = md_converter.convert(md_txt)
    """
    from .ansiext import AnsiExtension
    md = Markdown(output_format='ansi', extensions=[ExtraExtension(), AnsiExtension()])
    md.stripTopLevelTags = False
    return md


def text():
    """This makes a converter from markdown to text (unicode) format.
    It can be called like this:
    from errbot.rendering import text
    md_converter = text()  # you need to cache the converter

    pure_text = md_converter.convert(md_txt)
    """
    from .ansiext import AnsiExtension
    md = Markdown(output_format='text', extensions=[ExtraExtension(), AnsiExtension()])
    md.stripTopLevelTags = False
    return md


def imtext():
    """This makes a converter from markdown to imtext (unicode) format.
    imtest is the format like gtalk, slack or skype with simple _ or * markup.

    It can be called like this:
    from errbot.rendering import imtext
    md_converter = imtext()  # you need to cache the converter

    im_text = md_converter.convert(md_txt)
    """
    from .ansiext import AnsiExtension
    md = Markdown(output_format='imtext', extensions=[ExtraExtension(), AnsiExtension()])
    md.stripTopLevelTags = False
    return md


class Mde2mdConverter(object):
    def convert(self, mde):
        while True:
            m = ATTR_RE.search(mde)
            if m is None:
                break
            left, right = m.span()
            mde = mde[:left] + mde[right:]
        return mde


def md():
    """This makes a converter from markdown-extra to markdown, stripping the attributes from extra.
    """
    return Mde2mdConverter()


def xhtml():
    """This makes a converter from markdown to xhtml format.
    It can be called like this:
    from errbot.rendering import xhtml
    md_converter = xhtml()  # you need to cache the converter

    html = md_converter.convert(md_txt)
    """
    return Markdown(output_format='xhtml', extensions=[ExtraExtension()])


def md_escape(txt):
    """ Call this if you want to be sure your text won't be interpreted as markdown
    :param txt: bare text to escape.
    """
    return MD_ESCAPE_RE.sub(lambda match: '\\' + match.group(0), txt)
