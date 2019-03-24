from itertools import chain
from collections import namedtuple
from functools import partial
import io
import logging

from markdown import Markdown
from markdown.extensions import Extension
from markdown.postprocessors import Postprocessor
from markdown.inlinepatterns import SubstituteTagPattern
from markdown.extensions.fenced_code import FencedBlockPreprocessor

from ansi.colour import fg, bg, fx
from html import unescape


log = logging.getLogger(__name__)


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
                             'inline_code',
                             'end_inline_code',
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
                           end_fixed_width='',
                           inline_code='',
                           end_inline_code='')


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
                           end_fixed_width='',
                           inline_code='',
                           end_inline_code='')


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
                             end_fixed_width='```\n',
                             inline_code='`',
                             end_inline_code='`')


NEXT_ROW = "&NEXT_ROW;"


class Table(object):

    def __init__(self, chr_table):
        self.headers = []
        self.rows = []
        self.in_headers = False
        self.ct = chr_table

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
                txt, length = el
                # Account for multiline cells
                cnt = str(txt).count(NEXT_ROW)
                if cnt > 0:
                    length -= cnt * len(NEXT_ROW)
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
                    text, ln = header
                    output.write('┃ ' + text + ' ' * (maxes[i] - 2 - ln) + ' ')
                output.write('┃')
                output.write('\n')
            output.write('┡' + '╇'.join('━' * m for m in maxes) + '┩')
            output.write('\n')
        else:
            output.write('┌' + '┬'.join('─' * m for m in maxes) + '┐')
            output.write('\n')
        first = True
        for row in self.rows:
            max_row_height = 1
            for i, item in enumerate(row):
                text, _ = item
                row_height = str(text).count(NEXT_ROW) + 1
                if row_height > max_row_height:
                    max_row_height = row_height
            if not first:
                output.write('├' + '┼'.join('─' * m for m in maxes) + '┤')
                output.write('\n')
            first = False
            for j in range(max_row_height):
                for i, item in enumerate(row):
                    text, ln = item
                    multi = text.split(NEXT_ROW)
                    if len(multi) > j:
                        text = multi[j]
                        ln = len(text)
                    else:
                        ln = 1
                        text = ' '
                    output.write('│ ' + text + ' ' * (maxes[i] - 2 - ln) + ' ')
                output.write('│')
                output.write('\n')
        output.write('└' + '┴'.join('─' * m for m in maxes) + '┘')
        output.write('\n')
        return str(self.ct.fixed_width) + output.getvalue() + str(self.ct.end_fixed_width)


class BorderlessTable(object):

    def __init__(self, chr_table):
        self.headers = []
        self.rows = []
        self.in_headers = False
        self.ct = chr_table

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
                txt, length = el
                # Account for multiline cells
                cnt = str(txt).count(NEXT_ROW)
                if cnt > 0:
                    length -= cnt * len(NEXT_ROW)
                if maxes[i] < length:
                    maxes[i] = length

        # add up margins
        maxes = [m + 2 for m in maxes]

        output = io.StringIO()
        if self.headers:
            for row in self.headers:
                for i, header in enumerate(row):
                    text, ln = header
                    output.write(text + ' ' * (maxes[i] - 2 - ln) + ' ')
                output.write('\n')
        for row in self.rows:
            max_row_height = 1
            for i, item in enumerate(row):
                text, _ = item
                row_height = str(text).count(NEXT_ROW) + 1
                if row_height > max_row_height:
                    max_row_height = row_height
            for j in range(max_row_height):
                for i, item in enumerate(row):
                    text, ln = item
                    multi = text.split(NEXT_ROW)
                    if len(multi) > j:
                        text = multi[j]
                        ln = len(text)
                    else:
                        ln = 1
                        text = ' '
                    output.write(text + ' ' * (maxes[i] - 2 - ln) + ' ')
                output.write('\n')
        return str(self.ct.fixed_width) + output.getvalue() + str(self.ct.end_fixed_width)


def recurse(write, chr_table, element, table=None, borders=True):
    post_element = []
    if element.text:
        text = element.text
    else:
        text = ''
    items = element.items()
    for k, v in items:
        if k == 'color':
            color_attr = getattr(chr_table, 'fg_' + v, None)
            if color_attr is None:
                log.warning("there is no '%s' color in ansi.", v)
                continue
            write(color_attr)
            post_element.append(chr_table.fg_default)
        elif k == 'bgcolor':
            color_attr = getattr(chr_table, 'bg_' + v, None)
            if color_attr is None:
                log.warning("there is no '%s' bgcolor in ansi", v)
                continue
            write(color_attr)
            post_element.append(chr_table.bg_default)
    if element.tag == 'img':
        text = dict(items)['src']
    elif element.tag == 'strong':
        write(chr_table.fx_bold)
        post_element.append(chr_table.fx_normal)
    elif element.tag == 'code':
        write(chr_table.inline_code)
        post_element.append(chr_table.end_inline_code)
    elif element.tag == 'em':
        write(chr_table.fx_underline)
        post_element.append(chr_table.fx_not_underline)
    elif element.tag == 'p':
        write(' ')
        post_element.append('\n')
    elif element.tag == 'br' and table:  # Treat <br/> differently in a table.
        write(NEXT_ROW)
    elif element.tag == 'a':
        post_element.append(' (' + element.get('href') + ')')
    elif element.tag == 'li':
        write('• ')
        post_element.append('\n')
    elif element.tag == 'hr':
        write('─' * 80)
        write('\n')
    elif element.tag == 'ul':  # ignore the text part
        text = None
    elif element.tag == 'h1':
        write(chr_table.fx_bold)
        text = text.upper()
        post_element.append(chr_table.fx_normal)
        post_element.append('\n\n')
    elif element.tag == 'h2':
        write('\n')
        write('  ')
        write(chr_table.fx_bold)
        post_element.append(chr_table.fx_normal)
        post_element.append('\n\n')
    elif element.tag == 'h3':
        write('\n')
        write('    ')
        write(chr_table.fx_underline)
        post_element.append(chr_table.fx_not_underline)
        post_element.append('\n\n')
    elif element.tag in ('h4', 'h5', 'h6'):
        write('\n')
        write('      ')
        post_element.append('\n')
    elif element.tag == 'table':
        table = Table(chr_table) if borders else BorderlessTable(chr_table)
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
        recurse(write, chr_table, e, table, borders)
    if element.tag == 'table':
        write = orig_write
        write(str(table))

    if element.tag == 'thead':
        table.end_headers()

    for restore in post_element:
        write(restore)
    if element.tail:
        tail = element.tail.rstrip('\n')
        if tail:
            write(tail)


def translate(element, chr_table=ANSI_CHRS, borders=True):
    f = io.StringIO()

    def write(ansi_obj):
        return f.write(str(ansi_obj))
    recurse(write, chr_table, element, borders=borders)
    result = f.getvalue().rstrip('\n')  # remove the useless final \n
    return result + str(chr_table.fx_reset)


# patch us in
def enable_format(name, chr_table, borders=True):
    Markdown.output_formats[name] = partial(translate, chr_table=chr_table, borders=borders)


for n, ct in (('ansi', ANSI_CHRS), ('text', TEXT_CHRS), ('imtext', IMTEXT_CHRS)):
    enable_format(n, ct)


class AnsiPostprocessor(Postprocessor):
    """Markdown generates html entities, this reputs them back to their unicode equivalent"""

    def run(self, text):
        return unescape(text)


# This is an adapted FencedBlockPreprocessor that doesn't insert <code><pre>
class AnsiPreprocessor(FencedBlockPreprocessor):
    def run(self, lines):
        """ Match and store Fenced Code Blocks in the HtmlStash. """
        text = "\n".join(lines)
        while 1:
            m = self.FENCED_BLOCK_RE.search(text)
            if m:
                code = self._escape(m.group('code'))

                placeholder = self.markdown.htmlStash.store(code)
                text = f'{text[:m.start()]}\n{placeholder}\n{text[m.end():]}'
            else:
                break
        return text.split('\n')

    def _escape(self, txt):
        """ basic html escaping """
        txt = txt.replace('&', '&amp;')
        txt = txt.replace('<', '&lt;')
        txt = txt.replace('>', '&gt;')
        txt = txt.replace('"', '&quot;')
        return txt


class AnsiExtension(Extension):
    """(kinda hackish) This is just a private extension to postprocess the html text to ansi text"""

    def extendMarkdown(self, md, md_globals):
        md.registerExtension(self)
        md.postprocessors.add(
            "unescape_html", AnsiPostprocessor(), ">unescape"
        )
        md.preprocessors.add(
            "ansi_fenced_codeblock", AnsiPreprocessor(md), "<fenced_code_block"
        )
        md.inlinePatterns.add(
            # Leave <br/> tags as is for proper table multiline cell processing
            "br", SubstituteTagPattern(r'<br/>', "br"), "<html"
        )
        del(md.preprocessors['fenced_code_block'])  # remove the old fenced block
        del(md.treeprocessors['prettify'])  # remove prettify treeprocessor since it adds extra new lines
