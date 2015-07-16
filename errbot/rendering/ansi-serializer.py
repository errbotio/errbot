#!/usr/bin/env python
# -*- coding: utf-8 -*-

from markdown import Markdown
from markdown.extensions.extra import ExtraExtension

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

  def add_col(self, text):
    if not self.rows:
      self.rows = [[]]
    self.rows[-1].append(text)

  def add_header(self, text):
    if not self.headers:
      self.headers = [[]]
    self.headers[-1].append(text)

  def begin_headers(self):
    self.in_headers = True

  def end_headers(self):
    self.in_headers = False


def recurse_ansi(write, element, table = None):
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
  elif element.tag == 'ul': # ignore the text part
    text = None
  elif element.tag == 'table':
    table = Table()
  elif element.tag == 'thead':
    table.begin_headers()
  elif element.tag == 'tr':
    table.next_row()
  elif element.tag == 'td':
    table.add_col(text)
    text = None
  elif element.tag == 'th':
    table.add_header(text)
    text = None

  if text:
    write(text)

  for e in element:
    recurse_ansi(write, e, table)
  if element.tag == 'table':
    print('end of table')
    print('headers: %s' % repr(table.headers))
    print('rows: %s' % repr(table.rows))

  if element.tag == 'thead':
    table.end_headers()

  for restore in exit:
    write(str(restore))

def to_ansi(element):
  f = io.StringIO()
  def write(ansi_obj):
    return f.write(str(ansi_obj))
  recurse_ansi(write, element)
  write(fx.reset)
  return f.getvalue()

if __name__ == '__main__':
  Markdown.output_formats['ansi']=to_ansi
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
Content Cell  | Content Cell
Content Cell  | Content Cell

""")
  print('-----------------------------------------------------------')
  print(out)
  print('-----------------------------------------------------------')


