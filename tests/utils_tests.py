# coding=utf-8
from datetime import timedelta
import pytest

from errbot.backends.test import ShallowConfig
from errbot.bootstrap import CORE_STORAGE, bot_config_defaults
from errbot.specific_plugin_manager import SpecificPluginManager
from errbot.storage.base import StoragePluginBase
from errbot.utils import *
from errbot.storage import StoreMixin

log = logging.getLogger(__name__)


def vc(v1, v2):
    assert version2array(v1) < version2array(v2)


def vc_neg(version):
    with pytest.raises(ValueError):
        version2array(version)


def test_version_check():
    yield vc, '2.0.0', '2.0.1'
    yield vc, '2.0.0', '2.1.0'
    yield vc, '2.0.0', '3.0.0'
    yield vc, '2.0.0-alpha', '2.0.0-beta'
    yield vc, '2.0.0-beta', '2.0.0-rc1'
    yield vc, '2.0.0-rc1', '2.0.0-rc2'
    yield vc, '2.0.0-rc2', '2.0.0-rc3'
    yield vc, '2.0.0-rc2', '2.0.0'
    yield vc, '2.0.0-beta', '2.0.1'


def test_version_check_negative():
    yield vc_neg, '1.2.3.4'
    yield vc_neg, '1.2'
    yield vc_neg, '1.2.-beta'
    yield vc_neg, '1.2.3-toto'
    yield vc_neg, '1.2.3-rc'


def test_formattimedelta():
    td = timedelta(0, 60 * 60 + 13 * 60)
    assert '1 hours and 13 minutes' == format_timedelta(td)


def test_drawbar():
    assert drawbar(5, 10) == '[████████▒▒▒▒▒▒▒]'
    assert drawbar(0, 10) == '[▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒]'
    assert drawbar(10, 10) == '[███████████████]'


def unescape_test():
    assert unescape_xml('&#32;') == ' '


def test_storage():
    key = b'test' if PY2 else 'test'

    __import__('errbot.config-template')
    config = ShallowConfig()
    config.__dict__.update(sys.modules['errbot.config-template'].__dict__)
    bot_config_defaults(config)

    spm = SpecificPluginManager(config, 'storage', StoragePluginBase, CORE_STORAGE, None)
    storage_plugin = spm.get_plugin_by_name('Memory')

    persistent_object = StoreMixin()
    persistent_object.open_storage(storage_plugin, 'test')
    persistent_object[key] = 'à value'
    assert persistent_object[key] == 'à value'
    assert key in persistent_object
    del persistent_object[key]
    assert key not in persistent_object
    assert len(persistent_object) == 0


def test_recurse_check_structure_valid():
    sample = dict(string="Foobar", list=["Foo", "Bar"], dict={'foo': "Bar"}, none=None, true=True, false=False)
    to_check = dict(string="Foobar", list=["Foo", "Bar", "Bas"], dict={'foo': "Bar"}, none=None, true=True,
                    false=False)
    recurse_check_structure(sample, to_check)


def test_recurse_check_structure_missingitem():
    sample = dict(string="Foobar", list=["Foo", "Bar"], dict={'foo': "Bar"}, none=None, true=True, false=False)
    to_check = dict(string="Foobar", list=["Foo", "Bar"], dict={'foo': "Bar"}, none=None, true=True)
    with pytest.raises(ValidationException):
        recurse_check_structure(sample, to_check)


def test_recurse_check_structure_extrasubitem():
    sample = dict(string="Foobar", list=["Foo", "Bar"], dict={'foo': "Bar"}, none=None, true=True, false=False)
    to_check = dict(string="Foobar", list=["Foo", "Bar", "Bas"], dict={'foo': "Bar", 'Bar': "Foo"}, none=None,
                    true=True, false=False)
    with pytest.raises(ValidationException):
        recurse_check_structure(sample, to_check)


def test_recurse_check_structure_missingsubitem():
    sample = dict(string="Foobar", list=["Foo", "Bar"], dict={'foo': "Bar"}, none=None, true=True, false=False)
    to_check = dict(string="Foobar", list=["Foo", "Bar", "Bas"], dict={}, none=None, true=True, false=False)
    with pytest.raises(ValidationException):
        recurse_check_structure(sample, to_check)


def test_recurse_check_structure_wrongtype_1():
    sample = dict(string="Foobar", list=["Foo", "Bar"], dict={'foo': "Bar"}, none=None, true=True, false=False)
    to_check = dict(string=None, list=["Foo", "Bar"], dict={'foo': "Bar"}, none=None, true=True, false=False)
    with pytest.raises(ValidationException):
        recurse_check_structure(sample, to_check)


def test_recurse_check_structure_wrongtype_2():
    sample = dict(string="Foobar", list=["Foo", "Bar"], dict={'foo': "Bar"}, none=None, true=True, false=False)
    to_check = dict(string="Foobar", list={'foo': "Bar"}, dict={'foo': "Bar"}, none=None, true=True, false=False)
    with pytest.raises(ValidationException):
        recurse_check_structure(sample, to_check)


def test_recurse_check_structure_wrongtype_3():
    sample = dict(string="Foobar", list=["Foo", "Bar"], dict={'foo': "Bar"}, none=None, true=True, false=False)
    to_check = dict(string="Foobar", list=["Foo", "Bar"], dict=["Foo", "Bar"], none=None, true=True, false=False)
    with pytest.raises(ValidationException):
        recurse_check_structure(sample, to_check)


def test_split_string_after_returns_original_string_when_chunksize_equals_string_size():
    str_ = 'foobar2000' * 2
    splitter = split_string_after(str_, len(str_))
    split = [chunk for chunk in splitter]
    assert [str_] == split


def test_split_string_after_returns_original_string_when_chunksize_equals_string_size_plus_one():
    str_ = 'foobar2000' * 2
    splitter = split_string_after(str_, len(str_) + 1)
    split = [chunk for chunk in splitter]
    assert [str_] == split


def test_split_string_after_returns_two_chunks_when_chunksize_equals_string_size_minus_one():
    str_ = 'foobar2000' * 2
    splitter = split_string_after(str_, len(str_) - 1)
    split = [chunk for chunk in splitter]
    assert ['foobar2000foobar200', '0'] == split


def test_split_string_after_returns_two_chunks_when_chunksize_equals_half_length_of_string():
    str_ = 'foobar2000' * 2
    splitter = split_string_after(str_, int(len(str_) / 2))
    split = [chunk for chunk in splitter]
    assert ['foobar2000', 'foobar2000'] == split
