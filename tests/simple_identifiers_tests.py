import unittest

from errbot.backends import SimpleIdentifier, SimpleMUCOccupant


class TestSimpleIdentifiers(unittest.TestCase):
    def test_identifier_eq(self):
        a = SimpleIdentifier("foo")
        b = SimpleIdentifier("foo")
        self.assertTrue(a == b)
        self.assertEqual(a, b)

    def test_identifier_ineq(self):
        a = SimpleIdentifier("foo")
        b = SimpleIdentifier("bar")
        self.assertFalse(a == b)
        self.assertNotEqual(a, b)

    def test_mucidentifier_eq(self):
        a = SimpleMUCOccupant("foo", "room")
        b = SimpleMUCOccupant("foo", "room")
        self.assertTrue(a == b)
        self.assertEqual(a, b)

    def test_mucidentifier_ineq1(self):
        a = SimpleMUCOccupant("foo", "room")
        b = SimpleMUCOccupant("bar", "room")
        self.assertFalse(a == b)
        self.assertNotEqual(a, b)

    def test_mucidentifier_ineq2(self):
        a = SimpleMUCOccupant("foo", "room1")
        b = SimpleMUCOccupant("foo", "room2")
        self.assertFalse(a == b)
        self.assertNotEqual(a, b)
