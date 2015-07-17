# vim: noai:ts=4:sw=4
from markdown import Markdown
from markdown.extensions.extra import ExtraExtension

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
