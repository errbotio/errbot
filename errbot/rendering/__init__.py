# vim: noai:ts=4:sw=4
import re
from markdown import Markdown
from markdown.extensions.extra import ExtraExtension
from markdown.extensions.attr_list import AttrListTreeprocessor

ATTR_RE = re.compile(AttrListTreeprocessor.BASE_RE)
# Here are few helpers to simplify the conversion from markdown to various
# backend formats.


def ansi():
    """This makes a converter from markdown to ansi (console) format.
    It can be called like this:
    from errbot.rendering import ansi
    md_converter = ansi()  # you need to cache the converter

    ansi_txt = md_converter.convert(md_txt)
    """
    from .ansi import AnsiExtension
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
    from .ansi import AnsiExtension
    md = Markdown(output_format='text', extensions=[ExtraExtension(), AnsiExtension()])
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
