# vim: ts=4:sw=4
import logging
import unittest
from errbot.rendering import ansi, text, md

log = logging.getLogger(__name__)


class MdRendering(unittest.TestCase):
    def test_ansi(self):
        mdc = ansi()
        self.assertEquals(mdc.convert("*woot*"), "\x1b[4mwoot\x1b[24m\n\x1b[0m")

    def test_text(self):
        mdc = text()
        self.assertEquals(mdc.convert("*woot*"), "woot")
        self.assertEquals(mdc.convert("# woot"), "WOOT")

    def test_mde2md(self):
        mdc = md()
        self.assertEquals(mdc.convert("woot"), "woot")
        self.assertEquals(mdc.convert("woot{stuff} really{otherstuff}"), "woot really")
