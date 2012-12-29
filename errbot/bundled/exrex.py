#!/usr/bin/env python

# This file is part of exrex.
#
# exrex is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# exrex is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with exrex. If not, see < http://www.gnu.org/licenses/ >.
#
# (C) 2012- by Adam Tauber, <asciimoo@gmail.com>

from re import sre_parse
from itertools import product, chain, tee

__all__ = ('generate', 'CATEGORIES', 'count', 'parse')

CATEGORIES = {'category_space': sorted(sre_parse.WHITESPACE),
              'category_digit': sorted(sre_parse.DIGITS),
              'category_any': [chr(x) for x in range(32, 123)]}


def comb(g, i):
    for c in g:
        g2, i = tee(i)
        for c2 in g2:
            yield c + c2


def mappend(g, c):
    for cc in g:
        yield cc + c


def _in(d):
    ret = []
    for i in d:
        if i[0] == 'range':
            ret.extend(map(chr, range(i[1][0], i[1][1] + 1)))
        elif i[0] == 'literal':
            ret.append(chr(i[1]))
        elif i[0] == 'category':
            subs = CATEGORIES.get(i[1], [''])
            ret.extend(subs)
    return ret


def prods(orig, ran, items):
    for o in orig:
        for r in ran:
            for s in product(items, repeat=r):
                yield o + ''.join(s)


def _gen(d, limit=20, count=False):
    """docstring for _p"""
    ret = ['']
    params = []
    strings = 0
    for i in d:
        if i[0] == 'in':
            subs = _in(i[1])
            if count:
                strings = (strings or 1) * len(subs)
            ret = comb(ret, subs)
        elif i[0] == 'literal':
            ret = mappend(ret, chr(i[1]))
        elif i[0] == 'category':
            subs = CATEGORIES.get(i[1], [''])
            if count:
                strings = (strings or 1) * len(subs)
            ret = comb(ret, subs)
        elif i[0] == 'any':
            subs = CATEGORIES['category_any']
            if count:
                strings = (strings or 1) * len(subs)
            ret = comb(ret, subs)
        elif i[0] == 'max_repeat':
            chars = filter(None, _gen(list(i[1][2]), limit))
            if i[1][1] + 1 - i[1][0] > limit:
                ran = range(i[1][0], i[1][0] + limit)
            else:
                ran = range(i[1][0], i[1][1] + 1)
            if count:
                for i in ran:
                    strings += pow(len(chars), i)
            ret = prods(ret, ran, chars)
        elif i[0] == 'branch':
            subs = chain.from_iterable(_gen(list(x), limit) for x in i[1][1])
            if count:
                strings = (strings or 1) * len(subs)
            ret = comb(ret, subs)
        elif i[0] == 'subpattern':
            l = i[1:]
            subs = list(chain.from_iterable(_gen(list(x[1]), limit) for x in l))
            if count:
                strings = (strings or 1) * len(subs)
            ret = comb(ret, subs)
        else:
            print('[!] cannot handle expression "%r"' % i)

    if count:
        return strings

    return ret


def parse(s):
    """Regular expression parser

    :param s: Regular expression
    :type s: str
    :rtype: list
    """
    r = sre_parse.parse(s)
    return list(r)


def generate(s, limit=20):
    """Creates a generator that generates all matching strings to a given regular expression

    :param s: Regular expression
    :type s: str
    :param limit: Range limit
    :type limit: int
    :returns: string generator object
    """
    return _gen(parse(s), limit)


def count(s, limit=20):
    """Counts all matching strings to a given regular expression

    :param s: Regular expression
    :type s: str
    :param limit: Range limit
    :type limit: int
    :rtype: int
    :returns: number of matching strings
    """
    return _gen(parse(s), limit, count=True)


def argparser():
    import argparse
    from sys import stdout

    argp = argparse.ArgumentParser(description='exrex - regular expression string generator')
    argp.add_argument('-o', '--output', help='Output file - default is STDOUT', metavar='FILE', default=stdout, type=argparse.FileType('w'))
    argp.add_argument('-l', '--limit', help='Max limit for range size - default is 20', default=20, action='store', type=int, metavar='N')
    argp.add_argument('-c', '--count', help='Count matching strings', default=False, action='store_true')
    argp.add_argument('-d', '--delimiter', help='Delimiter - default is \\n', default='\n')
    argp.add_argument('-v', '--verbose', action='store_true', help='Verbose mode', default=False)
    argp.add_argument('regex', metavar='REGEX', help='REGEX string')
    return vars(argp.parse_args())
