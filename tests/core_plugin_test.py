import pytest

def test_admins_to_notify(testbot):
    """Test _admins_to_notify wrapper function"""
    admins = testbot._bot._admins_to_notify()
    assert len(admins) == 1
    assert 'gbin@localhost' in admins
    with pytest.raises(AssertionError):
        assert 'zoni@localdomain' in admins
