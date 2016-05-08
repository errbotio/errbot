# vim: ts=4:sw=4
import logging
from errbot.rendering import ansi, text, md, md_escape

log = logging.getLogger(__name__)


def test_ansi():
    mdc = ansi()
    assert mdc.convert("*woot*") == "\x1b[4mwoot\x1b[24m\x1b[0m"


def test_text():
    mdc = text()
    assert mdc.convert("*woot*") == "woot"
    assert mdc.convert("# woot") == "WOOT"


def test_mde2md():
    mdc = md()
    assert mdc.convert("woot") == "woot"
    assert mdc.convert("woot{:stuff} really{:otherstuff}") == "woot really"


def test_escaping():
    mdc = text()
    original = '#not a title\n*not italic*\n`not code`\ntoto{not annotation}'
    escaped = md_escape(original)
    assert original == mdc.convert(escaped)
