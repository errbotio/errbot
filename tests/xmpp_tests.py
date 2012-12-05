import unittest

class TestBase(unittest.TestCase):
    def test_identifier_parsing(self):
        id1 = Identifier(jid="gbin@gootz.net/toto")
        self.assertEqual(id1.getNode(), "gbin")
        self.assertEqual(id1.getDomain(), "gootz.net")
        self.assertEqual(id1.getResource(), "toto")



