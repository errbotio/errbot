import unittest

from errbot.backends.test import TestIdentifier, TestMUCOccupant


class TestSimpleIdentifiers(unittest.TestCase):
    def test_identifier_eq(self):
        a = TestIdentifier("foo")
        b = TestIdentifier("foo")
        self.assertTrue(a == b)
        self.assertEqual(a, b)

    def test_identifier_ineq(self):
        a = TestIdentifier("foo")
        b = TestIdentifier("bar")
        self.assertFalse(a == b)
        self.assertNotEqual(a, b)

    def test_mucidentifier_eq(self):
        a = TestMUCOccupant("foo", "room")
        b = TestMUCOccupant("foo", "room")
        self.assertTrue(a == b)
        self.assertEqual(a, b)

    def test_mucidentifier_ineq1(self):
        a = TestMUCOccupant("foo", "room")
        b = TestMUCOccupant("bar", "room")
        self.assertFalse(a == b)
        self.assertNotEqual(a, b)

    def test_mucidentifier_ineq2(self):
        a = TestMUCOccupant("foo", "room1")
        b = TestMUCOccupant("foo", "room2")
        self.assertFalse(a == b)
        self.assertNotEqual(a, b)
