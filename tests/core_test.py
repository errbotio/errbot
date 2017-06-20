import pytest


def test_admins_to_notify(testbot):
    """Test _admins_to_notify wrapper function"""
    notified_admins = testbot._bot._admins_to_notify()
    assert 'zoni@localdomain' in notified_admins
