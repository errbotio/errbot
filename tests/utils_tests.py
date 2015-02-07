# coding=utf-8
from datetime import timedelta
import unittest
from nose.tools import raises
from errbot.utils import *
from errbot.storage import StoreMixin


def vc(v1, v2):
    return version2array(v1) < version2array(v2)


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
    raises(ValueError)(version2array)('1.2.3.4', )
    raises(ValueError)(version2array)('1.2', )
    raises(ValueError)(version2array)('1.2.-beta', )
    raises(ValueError)(version2array)('1.2.3-toto', )
    raises(ValueError)(version2array)('1.2.3-rc', )


class TestUtils(unittest.TestCase):
    def test_formattimedelta(self):
        td = timedelta(0, 60 * 60 + 13 * 60)
        self.assertEqual('1 hours and 13 minutes', format_timedelta(td))

    def test_drawbar(self):
        self.assertEqual(drawbar(5, 10), '[████████▒▒▒▒▒▒▒]')
        self.assertEqual(drawbar(0, 10), '[▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒]')
        self.assertEqual(drawbar(10, 10), '[███████████████]')

    def unescape_test(self):
        self.assertEqual(unescape_xml('&#32;'), ' ')

    def test_storage(self):
        class MyPersistentClass(StoreMixin):
            pass

        from config import BOT_DATA_DIR

        key = b'test' if PY2 else 'test'

        persistent_object = MyPersistentClass()
        persistent_object.open_storage(BOT_DATA_DIR + os.path.sep + 'test.db')
        persistent_object[key] = 'à value'
        self.assertEquals(persistent_object[key], 'à value')
        self.assertIn(key, persistent_object)
        del persistent_object[key]
        self.assertNotIn(key, persistent_object)
        self.assertEquals(len(persistent_object), 0)

    @raises(SystemExit)
    def test_pid(self):
        from platform import system
        from config import BOT_DATA_DIR

        if system() != 'Windows':
            pid_path = BOT_DATA_DIR + os.path.sep + 'err_test.pid'

            from errbot.pid import PidFile

            pidfile1 = PidFile(pid_path)
            pidfile2 = PidFile(pid_path)

            with pidfile1:
                logging.debug('ok locked the pid')
                with pidfile2:
                    logging.fatal('Should never execute')

    def test_recurse_check_structure_valid(self):
        sample = dict(string="Foobar", list=["Foo", "Bar"], dict={'foo': "Bar"}, none=None, true=True, false=False)
        to_check = dict(string="Foobar", list=["Foo", "Bar", "Bas"], dict={'foo': "Bar"}, none=None, true=True,
                        false=False)
        recurse_check_structure(sample, to_check)

    @raises(ValidationException)
    def test_recurse_check_structure_missingitem(self):
        sample = dict(string="Foobar", list=["Foo", "Bar"], dict={'foo': "Bar"}, none=None, true=True, false=False)
        to_check = dict(string="Foobar", list=["Foo", "Bar"], dict={'foo': "Bar"}, none=None, true=True)
        recurse_check_structure(sample, to_check)

    @raises(ValidationException)
    def test_recurse_check_structure_extrasubitem(self):
        sample = dict(string="Foobar", list=["Foo", "Bar"], dict={'foo': "Bar"}, none=None, true=True, false=False)
        to_check = dict(string="Foobar", list=["Foo", "Bar", "Bas"], dict={'foo': "Bar", 'Bar': "Foo"}, none=None,
                        true=True, false=False)
        recurse_check_structure(sample, to_check)

    @raises(ValidationException)
    def test_recurse_check_structure_missingsubitem(self):
        sample = dict(string="Foobar", list=["Foo", "Bar"], dict={'foo': "Bar"}, none=None, true=True, false=False)
        to_check = dict(string="Foobar", list=["Foo", "Bar", "Bas"], dict={}, none=None, true=True, false=False)
        recurse_check_structure(sample, to_check)

    @raises(ValidationException)
    def test_recurse_check_structure_wrongtype_1(self):
        sample = dict(string="Foobar", list=["Foo", "Bar"], dict={'foo': "Bar"}, none=None, true=True, false=False)
        to_check = dict(string=None, list=["Foo", "Bar"], dict={'foo': "Bar"}, none=None, true=True, false=False)
        recurse_check_structure(sample, to_check)

    @raises(ValidationException)
    def test_recurse_check_structure_wrongtype_2(self):
        sample = dict(string="Foobar", list=["Foo", "Bar"], dict={'foo': "Bar"}, none=None, true=True, false=False)
        to_check = dict(string="Foobar", list={'foo': "Bar"}, dict={'foo': "Bar"}, none=None, true=True, false=False)
        recurse_check_structure(sample, to_check)

    @raises(ValidationException)
    def test_recurse_check_structure_wrongtype_3(self):
        sample = dict(string="Foobar", list=["Foo", "Bar"], dict={'foo': "Bar"}, none=None, true=True, false=False)
        to_check = dict(string="Foobar", list=["Foo", "Bar"], dict=["Foo", "Bar"], none=None, true=True, false=False)
        recurse_check_structure(sample, to_check)

    def test_split_string_after_returns_original_string_when_chunksize_equals_string_size(self):
        str_ = 'foobar2000' * 2
        splitter = split_string_after(str_, len(str_))
        split = [chunk for chunk in splitter]
        self.assertEqual([str_], split)

    def test_split_string_after_returns_original_string_when_chunksize_equals_string_size_plus_one(self):
        str_ = 'foobar2000' * 2
        splitter = split_string_after(str_, len(str_) + 1)
        split = [chunk for chunk in splitter]
        self.assertEqual([str_], split)

    def test_split_string_after_returns_two_chunks_when_chunksize_equals_string_size_minus_one(self):
        str_ = 'foobar2000' * 2
        splitter = split_string_after(str_, len(str_) - 1)
        split = [chunk for chunk in splitter]
        self.assertEqual(['foobar2000foobar200', '0'], split)

    def test_split_string_after_returns_two_chunks_when_chunksize_equals_half_length_of_string(self):
        str_ = 'foobar2000' * 2
        splitter = split_string_after(str_, int(len(str_) / 2))
        split = [chunk for chunk in splitter]
        self.assertEqual(['foobar2000', 'foobar2000'], split)
