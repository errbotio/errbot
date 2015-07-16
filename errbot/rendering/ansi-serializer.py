#!/usr/bin/env python
# -*- coding: utf-8 -*-
# vim: noai:ts=2:sw=2

from markdown import Markdown
from markdown.extensions.extra import ExtraExtension
from itertools import chain

from ansi.color import fg, fx
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
            if v == 'red':
                write(fg.red)
            elif v == 'blue':
                write(fg.blue)
        exit.append(fg.default)

    if element.tag == 'strong':
        write(fx.bold)
        exit.append(fx.normal)
    elif element.tag == 'em':
        write(fx.italic)
        exit.append(fx.not_italic)
    elif element.tag == 'u':
        write(fx.underline)
        exit.append(fx.not_underline)
    elif element.tag == 'p':
        exit.append('\n')
    elif element.tag == 'li':
        write('• ')
        exit.append('\n')
    elif element.tag == 'hr':
        write('─' * 80)
        write('\n')
    elif element.tag == 'ul':  # ignore the text part
        text = None
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

if __name__ == '__main__':
    Markdown.output_formats['ansi'] = to_ansi
    md = Markdown(output_format='ansi', extensions=[ExtraExtension()])
    md.stripTopLevelTags = False
    out = md.convert(
        """
Normal Markdown:
**bold**

_italic_

Red paragraph
{color='red'}

Inline `blue text`{color='blue'}

Inline *emphasis blue text*{color='blue'}

This is my list:

-  element one
-  element two
-  element three

***
after ruler


First Header  | Second Header
------------- | -------------
Content Cell  | **Content Cell**
Content Cell  | _Content Cell_

""")
    print('-----------------------------------------------------------')
    print(out)
    print('-----------------------------------------------------------')
