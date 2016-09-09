from errbot.backends.test import TestPerson, TestOccupant


def test_identifier_eq():
    a = TestPerson("foo")
    b = TestPerson("foo")
    assert a == b


def test_identifier_ineq():
    a = TestPerson("foo")
    b = TestPerson("bar")
    assert not a == b
    assert a != b


def test_mucidentifier_eq():
    a = TestOccupant("foo", "room")
    b = TestOccupant("foo", "room")
    assert a == b


def test_mucidentifier_ineq1():
    a = TestOccupant("foo", "room")
    b = TestOccupant("bar", "room")
    assert not a == b
    assert a != b


def test_mucidentifier_ineq2():
    a = TestOccupant("foo", "room1")
    b = TestOccupant("foo", "room2")
    assert not a == b
    assert a != b
