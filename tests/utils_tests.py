# coding=utf-8
import unittest
from errbot.utils import *

class TestUtils(unittest.TestCase):

    def test_formattimedelta(self):
        td = timedelta(0,60*60 + 13*60)
        self.assertEqual('1 hours and 13 minutes', format_timedelta(td))

    def test_drawbar(self):
        self.assertEqual(drawbar(5,10),u'[████████▒▒▒▒▒▒▒]')
        self.assertEqual(drawbar(0,10),u'[▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒]')
        self.assertEqual(drawbar(10,10),u'[███████████████]')