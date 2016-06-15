from errbot.storage import StoreMixin
from errbot.storage.memory import MemoryStoragePlugin


def test_simple_store_retreive():
    sm = StoreMixin()
    sm.open_storage(MemoryStoragePlugin(None), 'ns')
    sm['toto'] = 'titui'
    assert sm['toto'] == 'titui'


def test_mutable():
    sm = StoreMixin()
    sm.open_storage(MemoryStoragePlugin(None), 'ns')
    sm['toto'] = [1, 3]

    with sm.mutable('toto') as titi:
        titi[1] = 5

    assert sm['toto'] == [1, 5]
