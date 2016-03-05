import unittest

from errbot.backends.test import TestPerson, TestOccupant


class TestSimpleIdentifiers(unittest.TestCase):
    def test_identifier_eq(self):
        a = TestPerson("foo")
        b = TestPerson("foo")
        self.assertTrue(a == b)
        self.assertEqual(a, b)

    def test_identifier_ineq(self):
        a = TestPerson("foo")
        b = TestPerson("bar")
        self.assertFalse(a == b)
        self.assertNotEqual(a, b)

    def test_mucidentifier_eq(self):
        a = TestOccupant("foo", "room")
        b = TestOccupant("foo", "room")
        self.assertTrue(a == b)
        self.assertEqual(a, b)

    def test_mucidentifier_ineq1(self):
        a = TestOccupant("foo", "room")
        b = TestOccupant("bar", "room")
        self.assertFalse(a == b)
        self.assertNotEqual(a, b)

    def test_mucidentifier_ineq2(self):
        a = TestOccupant("foo", "room1")
        b = TestOccupant("foo", "room2")
        self.assertFalse(a == b)
        self.assertNotEqual(a, b)
