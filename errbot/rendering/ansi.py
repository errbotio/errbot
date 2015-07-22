#!/usr/bin/env python
# -*- coding: utf-8 -*-
# vim: ts=4:sw=4

from markdown import Markdown
from markdown.extensions.extra import ExtraExtension
from markdown.extensions import Extension
from markdown.postprocessors import Postprocessor
from itertools import chain
from os import path
from ansi.color import fg, bg, fx
from collections import namedtuple
from functools import partial
import io
import logging

log = logging.getLogger(__name__)

try:
    from html import unescape  # py3.5
except:
    try:
        from html.parser import HTMLParser  # py3.4
    except ImportError:
        from HTMLParser import HTMLParser  # py2
    finally:
        unescape = HTMLParser().unescape

# chr that should not count as a space
class NSC(object):
    def __init__(self, s):
        self.s = s
    def __str__(self):
        return self.s

# The translation table for the special characters.
CharacterTable = namedtuple('CharacterTable',
                            ['fg_black',
                             'fg_red',
                             'fg_green',
                             'fg_yellow',
                             'fg_blue',
                             'fg_magenta',
                             'fg_cyan',
                             'fg_white',
                             'fg_default',
                             'bg_black',
                             'bg_red',
                             'bg_green',
                             'bg_yellow',
                             'bg_blue',
                             'bg_magenta',
                             'bg_cyan',
                             'bg_white',
                             'bg_default',
                             'fx_reset',
                             'fx_bold',
                             'fx_italic',
                             'fx_underline',
                             'fx_not_italic',
                             'fx_not_underline',
                             'fx_normal',
                             'fixed_width',
                             'end_fixed_width',
                             ])

ANSI_CHRS = CharacterTable(fg_black=fg.black,
                           fg_red=fg.red,
                           fg_green=fg.green,
                           fg_yellow=fg.yellow,
                           fg_blue=fg.blue,
                           fg_magenta=fg.magenta,
                           fg_cyan=fg.cyan,
                           fg_white=fg.white,
                           fg_default=fg.default,
                           bg_black=bg.black,
                           bg_red=bg.red,
                           bg_green=bg.green,
                           bg_yellow=bg.yellow,
                           bg_blue=bg.blue,
                           bg_magenta=bg.magenta,
                           bg_cyan=bg.cyan,
                           bg_white=bg.white,
                           bg_default=bg.default,
                           fx_reset=fx.reset,
                           fx_bold=fx.bold,
                           fx_italic=fx.italic,
                           fx_underline=fx.underline,
                           fx_not_italic=fx.not_italic,
                           fx_not_underline=fx.not_underline,
                           fx_normal=fx.normal,
                           fixed_width='',
                           end_fixed_width='')

# Pure Text doesn't have any graphical chrs.
TEXT_CHRS = CharacterTable(fg_black='',
                           fg_red='',
                           fg_green='',
                           fg_yellow='',
                           fg_blue='',
                           fg_magenta='',
                           fg_cyan='',
                           fg_white='',
                           fg_default='',
                           bg_black='',
                           bg_red='',
                           bg_green='',
                           bg_yellow='',
                           bg_blue='',
                           bg_magenta='',
                           bg_cyan='',
                           bg_white='',
                           bg_default='',
                           fx_reset='',
                           fx_bold='',
                           fx_italic='',
                           fx_underline='',
                           fx_not_italic='',
                           fx_not_underline='',
                           fx_normal='',
                           fixed_width='',
                           end_fixed_width='')

# IMText have some formatting available
IMTEXT_CHRS = CharacterTable(fg_black='',
                             fg_red='',
                             fg_green='',
                             fg_yellow='',
                             fg_blue='',
                             fg_magenta='',
                             fg_cyan='',
                             fg_white='',
                             fg_default='',
                             bg_black='',
                             bg_red='',
                             bg_green='',
                             bg_yellow='',
                             bg_blue='',
                             bg_magenta='',
                             bg_cyan='',
                             bg_white='',
                             bg_default='',
                             fx_reset='',
                             fx_bold=NSC('*'),
                             fx_italic='',
                             fx_underline=NSC('_'),
                             fx_not_italic='',
                             fx_not_underline=NSC('_'),
                             fx_normal=NSC('*'),
                             fixed_width='```\n',
                             end_fixed_width='```\n')



class Table(object):

    def __init__(self,  ct):
        self.headers = []
        self.rows = []
        self.in_headers = False
        self.ct = ct

    def next_row(self):
        if self.in_headers:
            self.headers.append([])  # is that exists ?
        else:
            self.rows.append([])

    def add_col(self):
        if not self.rows:
            self.rows = [[]]
        else:
            self.rows[-1].append(('', 0))

    def add_header(self):
        if not self.headers:
            self.headers = [[]]
        else:
            self.headers[-1].append(('', 0))

    def begin_headers(self):
        self.in_headers = True

    def end_headers(self):
        self.in_headers = False

    def write(self, text):
        cells = self.headers if self.in_headers else self.rows

        text_cell, count = cells[-1][-1]
        if isinstance(text, str):
            text_cell += text
            count += len(text)
        else:
            text_cell += str(text)  # This is a non space chr
        cells[-1][-1] = text_cell, count

    def __str__(self):
        nbcols = max(len(row) for row in chain(self.headers, self.rows))
        maxes = [0, ] * nbcols

        for row in chain(self.headers, self.rows):
            for i, el in enumerate(row):
                _, length = el
                if maxes[i] < length:
                    maxes[i] = length

        # add up margins
        maxes = [m + 2 for m in maxes]

        output = io.StringIO()
        if self.headers:
            output.write('┏' + '┳'.join('━' * m for m in maxes) + '┓')
            output.write('\n')
            first = True
            for row in self.headers:
                if not first:
                    output.write('┣' + '╋'.join('━' * m for m in maxes) + '┫')
                    output.write('\n')
                first = False
                for i, header in enumerate(row):
                    text, l = header
                    output.write('┃ ' + text + ' ' * (maxes[i] - 2 - l) + ' ')
                output.write('┃')
                output.write('\n')
            output.write('┡' + '╇'.join('━' * m for m in maxes) + '┩')
            output.write('\n')
        else:
            output.write('┌' + '┬'.join('─' * m for m in maxes) + '┐')
            output.write('\n')
        first = True
        for row in self.rows:
            if not first:
                output.write('├' + '┼'.join('─' * m for m in maxes) + '┤')
                output.write('\n')
            first = False
            for i, item in enumerate(row):
                text, l = item
                output.write('│ ' + text + ' ' * (maxes[i] - 2 - l) + ' ')
            output.write('│')
            output.write('\n')
        output.write('└' + '┴'.join('─' * m for m in maxes) + '┘')
        output.write('\n')
        return str(self.ct.fixed_width) + output.getvalue() + str(self.ct.end_fixed_width)


def recurse(write, ct, element, table=None):
    exit = []
    if element.text:
        text = element.text
    else:
        text = ''

    items = element.items()
    for k, v in items:
        if k == 'color':
            color_attr = getattr(ct, 'fg_' + v)
            if color_attr is None:
                log.warn("there is no '%s' color in ansi" % v)
            write(color_attr)
            exit.append(ct.fg_default)
        elif k == 'bgcolor':
            color_attr = getattr(ct, 'bg_' + v)
            if color_attr is None:
                log.warn("there is no '%s' bgcolor in ansi" % v)
            write(color_attr)
            exit.append(ct.bg_default)
    if element.tag == 'img':
        text = dict(items)['src']
    elif element.tag == 'strong':
        write(ct.fx_bold)
        exit.append(ct.fx_normal)
    elif element.tag == 'em':
        write(ct.fx_underline)
        exit.append(ct.fx_not_underline)
    elif element.tag == 'p':
        write(' ')
        exit.append('\n')
    elif element.tag == 'a':
        exit.append(' (' + element.get('href') + ')')
    elif element.tag == 'li':
        write('• ')
        exit.append('\n')
    elif element.tag == 'hr':
        write('─' * 80)
        write('\n')
    elif element.tag == 'ul':  # ignore the text part
        text = None
    elif element.tag == 'h1':
        write(ct.fx_bold)
        text = text.upper()
        exit.append(ct.fx_normal)
        exit.append('\n\n')
    elif element.tag == 'h2':
        write('\n')
        write('  ')
        write(ct.fx_bold)
        exit.append(ct.fx_normal)
        exit.append('\n\n')
    elif element.tag == 'h3':
        write('\n')
        write('    ')
        write(ct.fx_underline)
        exit.append(ct.fx_not_underline)
        exit.append('\n')
    elif element.tag in ('h4', 'h5', 'h6'):
        write('\n')
        write('      ')
        exit.append('\n')
    elif element.tag == 'table':
        table = Table(ct)
        orig_write = write
        write = table.write
        text = None
    elif element.tag == 'tbody':
        text = None
    elif element.tag == 'thead':
        table.begin_headers()
        text = None
    elif element.tag == 'tr':
        table.next_row()
        text = None
    elif element.tag == 'td':
        table.add_col()
    elif element.tag == 'th':
        table.add_header()

    if text:
        write(text)
    for e in element:
        recurse(write, ct, e, table)
    if element.tag == 'table':
        write = orig_write
        write(str(table))

    if element.tag == 'thead':
        table.end_headers()

    for restore in exit:
        write(restore)
    if element.tail:
        tail = element.tail.rstrip('\n')
        if tail:
            write(tail)


def translate(element, ct=ANSI_CHRS):
    f = io.StringIO()

    def write(ansi_obj):
        return f.write(str(ansi_obj))
    recurse(write, ct, element)
    write(fx.reset)
    return f.getvalue()


# patch us in
Markdown.output_formats['ansi'] = partial(translate, ct=ANSI_CHRS)
Markdown.output_formats['text'] = partial(translate, ct=TEXT_CHRS)
Markdown.output_formats['imtext'] = partial(translate, ct=IMTEXT_CHRS)


class AnsiPostprocessor(Postprocessor):
    """Markdown generates html entities, this reputs them back to their unicode equivalent"""

    def run(self, text):
        return unescape(text)


class AnsiExtension(Extension):
    """(kinda hackish) This is just a private extension to postprocess the html text to ansi text"""

    def extendMarkdown(self, md, md_globals):
        md.registerExtension(self)
        md.postprocessors.add(
            "unescape html", AnsiPostprocessor(), ">unescape"
        )
        log.debug("Will apply those postprocessors:\n%s" % md.postprocessors)
