import unittest

from errbot.backend_manager import BackendManager
import logging
logging.basicConfig(level=logging.DEBUG)


class TestBackendsManager(unittest.TestCase):
    def test_builtins(self):
        bpm = BackendManager({})
        backend_plug = bpm.getPluginCandidates()
        names = [plug.name for (_, _, plug) in backend_plug]
        assert 'Text' in names
        assert 'Test' in names
        assert 'Null' in names
