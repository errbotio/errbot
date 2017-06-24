"""Test _admins_to_notify wrapper functionality"""
import pytest


extra_config = {'BOT_ADMINS_NOTIFICATIONS': 'zoni@localdomain'}


def test_admins_to_notify(testbot):
    """Test which admins will be notified"""
    notified_admins = testbot._bot._admins_to_notify()
    assert 'zoni@localdomain' in notified_admins


def test_admins_not_notified(testbot):
    """Test which admins will not be notified"""
    notified_admins = testbot._bot._admins_to_notify()
    assert 'gbin@local' not in notified_admins
