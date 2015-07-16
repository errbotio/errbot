#!/usr/bin/env python
# -*- coding: utf-8 -*-
# vim: noai:ts=4:sw=4

from markdown import Markdown
from markdown.extensions.extra import ExtraExtension
from markdown.extensions import Extension
from markdown.postprocessors import Postprocessor
from itertools import chain
import html
from os import path
from ansi.color import fg, bg, fx
import io


class Table(object):

    def __init__(self):
        self.headers = []
        self.rows = []
        self.in_headers = False

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
            text_cell += str(text)  # Graphic
        cells[-1][-1] = text_cell, count

    def __str__(self):
        nbcols = max(len(row) for row in chain(self.headers, self.rows))
        print("nbcols = %i" % nbcols)
        maxes = [0, ] * nbcols

        for row in chain(self.headers, self.rows):
            for i, el in enumerate(row):
                _, length = el
                if maxes[i] < length:
                    maxes[i] = length
        print("maxes %s" % maxes)

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
        return output.getvalue()


def recurse_ansi(write, element, table=None):
    print("tag = '%s'" % element.tag)
    print("text = '%s'" % element.text)
    items = element.items()
    exit = []
    if element.text:
        text = element.text
    else:
        text = ''

    for k, v in items:
        print("k = %s / v = %s" % (k, v))
        if k == 'color':
            color_attr = getattr(fg, v)
            if color_attr is None:
                log.warn("there is no '%s' color in ansi" % v)
            write(color_attr)
            exit.append(fg.default)
        elif k == 'bgcolor':
            color_attr = getattr(bg, v)
            if color_attr is None:
                log.warn("there is no '%s' bgcolor in ansi" % v)
            write(color_attr)
            exit.append(bg.default)
    if element.tag == 'img':
        text = dict(items)['src']
    elif element.tag == 'strong':
        write(fx.bold)
        exit.append(fx.normal)
    elif element.tag == 'em':
        write(fx.underline)
        exit.append(fx.not_underline)
    elif element.tag == 'p':
        write(' ')
        exit.append('\n')
    elif element.tag == 'li':
        write('• ')
        exit.append('\n')
    elif element.tag == 'hr':
        write('─' * 80)
        write('\n')
    elif element.tag == 'ul':  # ignore the text part
        text = None
    elif element.tag == 'h1':
        write(fx.bold)
        text = text.upper()
        exit.append(fx.normal)
        exit.append('\n\n')
    elif element.tag == 'h2':
        write('\n')
        write('  ')
        write(fx.bold)
        exit.append(fx.normal)
        exit.append('\n\n')
    elif element.tag == 'h3':
        write('\n')
        write('    ')
        write(fx.underline)
        exit.append(fx.not_underline)
        exit.append('\n')
    elif element.tag in ('h4', 'h5', 'h6'):
        write('\n')
        write('      ')
        exit.append('\n')
    elif element.tag == 'table':
        table = Table()
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
        recurse_ansi(write, e, table)
    if element.tag == 'table':
        print('end of table')
        print('headers: %s' % repr(table.headers))
        print('rows: %s' % repr(table.rows))
        write = orig_write
        write(table)

    if element.tag == 'thead':
        table.end_headers()

    for restore in exit:
        write(restore)


def to_ansi(element):
    f = io.StringIO()

    def write(ansi_obj):
        return f.write(str(ansi_obj))
    recurse_ansi(write, element)
    write(fx.reset)
    return f.getvalue()

# patch us in
Markdown.output_formats['ansi'] = to_ansi


class AnsiPostprocessor(Postprocessor):

    def run(self, text):
        return html.unescape(text)


class AnsiExtension(Extension):

    def extendMarkdown(self, md, md_globals):
        md.registerExtension(self)
        md.postprocessors.add(
            "unescape html", AnsiPostprocessor(), ">amp_substitute"
        )


if __name__ == '__main__':
    md = Markdown(output_format='ansi', extensions=[ExtraExtension(), AnsiExtension()])
    md.stripTopLevelTags = False
    with open(path.join(path.dirname(path.realpath(__file__)), 'test.md')) as f:
        out = md.convert(f.read())
    print('-----------------------------------------------------------')
    print(out)
    print('-----------------------------------------------------------')
