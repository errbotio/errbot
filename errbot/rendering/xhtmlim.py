import re
from html.entities import entitydefs

# Helpers for xhtml-im

SAFE_ENTITIES = {
    e: entitydefs[e] for e in entitydefs if e not in ("amp", "quot", "apos", "gt", "lt")
}

_invalid_codepoints = {
    # 0x0001 to 0x0008
    0x1,
    0x2,
    0x3,
    0x4,
    0x5,
    0x6,
    0x7,
    0x8,
    # 0x000E to 0x001F
    0xE,
    0xF,
    0x10,
    0x11,
    0x12,
    0x13,
    0x14,
    0x15,
    0x16,
    0x17,
    0x18,
    0x19,
    0x1A,
    0x1B,
    0x1C,
    0x1D,
    0x1E,
    0x1F,
    # 0x007F to 0x009F
    0x7F,
    0x80,
    0x81,
    0x82,
    0x83,
    0x84,
    0x85,
    0x86,
    0x87,
    0x88,
    0x89,
    0x8A,
    0x8B,
    0x8C,
    0x8D,
    0x8E,
    0x8F,
    0x90,
    0x91,
    0x92,
    0x93,
    0x94,
    0x95,
    0x96,
    0x97,
    0x98,
    0x99,
    0x9A,
    0x9B,
    0x9C,
    0x9D,
    0x9E,
    0x9F,
    # 0xFDD0 to 0xFDEF
    0xFDD0,
    0xFDD1,
    0xFDD2,
    0xFDD3,
    0xFDD4,
    0xFDD5,
    0xFDD6,
    0xFDD7,
    0xFDD8,
    0xFDD9,
    0xFDDA,
    0xFDDB,
    0xFDDC,
    0xFDDD,
    0xFDDE,
    0xFDDF,
    0xFDE0,
    0xFDE1,
    0xFDE2,
    0xFDE3,
    0xFDE4,
    0xFDE5,
    0xFDE6,
    0xFDE7,
    0xFDE8,
    0xFDE9,
    0xFDEA,
    0xFDEB,
    0xFDEC,
    0xFDED,
    0xFDEE,
    0xFDEF,
    # others
    0xB,
    0xFFFE,
    0xFFFF,
    0x1FFFE,
    0x1FFFF,
    0x2FFFE,
    0x2FFFF,
    0x3FFFE,
    0x3FFFF,
    0x4FFFE,
    0x4FFFF,
    0x5FFFE,
    0x5FFFF,
    0x6FFFE,
    0x6FFFF,
    0x7FFFE,
    0x7FFFF,
    0x8FFFE,
    0x8FFFF,
    0x9FFFE,
    0x9FFFF,
    0xAFFFE,
    0xAFFFF,
    0xBFFFE,
    0xBFFFF,
    0xCFFFE,
    0xCFFFF,
    0xDFFFE,
    0xDFFFF,
    0xEFFFE,
    0xEFFFF,
    0xFFFFE,
    0xFFFFF,
    0x10FFFE,
    0x10FFFF,
}

_invalid_charrefs = {
    0x00: "\ufffd",  # REPLACEMENT CHARACTER
    0x0D: "\r",  # CARRIAGE RETURN
    0x80: "\u20ac",  # EURO SIGN
    0x81: "\x81",  # <control>
    0x82: "\u201a",  # SINGLE LOW-9 QUOTATION MARK
    0x83: "\u0192",  # LATIN SMALL LETTER F WITH HOOK
    0x84: "\u201e",  # DOUBLE LOW-9 QUOTATION MARK
    0x85: "\u2026",  # HORIZONTAL ELLIPSIS
    0x86: "\u2020",  # DAGGER
    0x87: "\u2021",  # DOUBLE DAGGER
    0x88: "\u02c6",  # MODIFIER LETTER CIRCUMFLEX ACCENT
    0x89: "\u2030",  # PER MILLE SIGN
    0x8A: "\u0160",  # LATIN CAPITAL LETTER S WITH CARON
    0x8B: "\u2039",  # SINGLE LEFT-POINTING ANGLE QUOTATION MARK
    0x8C: "\u0152",  # LATIN CAPITAL LIGATURE OE
    0x8D: "\x8d",  # <control>
    0x8E: "\u017d",  # LATIN CAPITAL LETTER Z WITH CARON
    0x8F: "\x8f",  # <control>
    0x90: "\x90",  # <control>
    0x91: "\u2018",  # LEFT SINGLE QUOTATION MARK
    0x92: "\u2019",  # RIGHT SINGLE QUOTATION MARK
    0x93: "\u201c",  # LEFT DOUBLE QUOTATION MARK
    0x94: "\u201d",  # RIGHT DOUBLE QUOTATION MARK
    0x95: "\u2022",  # BULLET
    0x96: "\u2013",  # EN DASH
    0x97: "\u2014",  # EM DASH
    0x98: "\u02dc",  # SMALL TILDE
    0x99: "\u2122",  # TRADE MARK SIGN
    0x9A: "\u0161",  # LATIN SMALL LETTER S WITH CARON
    0x9B: "\u203a",  # SINGLE RIGHT-POINTING ANGLE QUOTATION MARK
    0x9C: "\u0153",  # LATIN SMALL LIGATURE OE
    0x9D: "\x9d",  # <control>
    0x9E: "\u017e",  # LATIN SMALL LETTER Z WITH CARON
    0x9F: "\u0178",  # LATIN CAPITAL LETTER Y WITH DIAERESIS
}


def _replace_charref(s):
    s = s.group(1)
    if s[0] == "#":
        # numeric charref
        if s[1] in "xX":
            num = int(s[2:].rstrip(";"), 16)
        else:
            num = int(s[1:].rstrip(";"))
        if num in _invalid_charrefs:
            return _invalid_charrefs[num]
        if 0xD800 <= num <= 0xDFFF or num > 0x10FFFF:
            return "\uFFFD"
        if num in _invalid_codepoints:
            return ""
        return chr(num)
    else:
        # named charref
        if s in SAFE_ENTITIES:
            return SAFE_ENTITIES[s]
        # find the longest matching name (as defined by the standard)
        for x in range(len(s) - 1, 1, -1):
            if s[:x] in SAFE_ENTITIES:
                return SAFE_ENTITIES[s[:x]] + s[x:]
        else:
            return "&" + s


_charref = re.compile(
    r"&(#[0-9]+;?" r"|#[xX][0-9a-fA-F]+;?" r"|[^\t\n\f <&#;]{1,32};?)"
)


def unescape(s):
    if "&" not in s:
        return s
    return _charref.sub(_replace_charref, s)
