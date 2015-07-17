# vim: ts=4:sw=4
import logging
import unittest
from errbot import rendering

log = logging.getLogger(__name__)


class MdRendering(unittest.TestCase):
    def test_ansi(self):
        md = rendering.ansi()
        self.assertEquals(md.convert("*woot*"), "\x1b[4mwoot\x1b[24m\n\x1b[0m")

    def test_text(self):
        md = rendering.text()
        self.assertEquals(md.convert("*woot*"), "woot")
        self.assertEquals(md.convert("# woot"), "WOOT")
