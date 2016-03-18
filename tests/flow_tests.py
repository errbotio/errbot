import logging
import unittest

from errbot.backends.test import TestPerson
from errbot.flow import FlowMessage

log = logging.getLogger(__name__)


class FlowTest(unittest.TestCase):
    def test_flowmessage(self):
        fm = FlowMessage(frm=TestPerson('la'))
        fm['flowdata'] = 'youpi'
        self.assertEqual(fm['flowdata'], 'youpi')
