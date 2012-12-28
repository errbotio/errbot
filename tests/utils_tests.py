# coding=utf-8
from datetime import timedelta
import unittest
from nose.tools import raises
from errbot.utils import *
from errbot.storage import StoreMixin

class TestUtils(unittest.TestCase):
    def test_formattimedelta(self):
        td = timedelta(0, 60 * 60 + 13 * 60)
        self.assertEqual('1 hours and 13 minutes', format_timedelta(td))

    def test_drawbar(self):
        self.assertEqual(drawbar(5, 10), '[████████▒▒▒▒▒▒▒]')
        self.assertEqual(drawbar(0, 10), '[▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒]')
        self.assertEqual(drawbar(10, 10), '[███████████████]')

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
        to_check = dict(string="Foobar", list=["Foo", "Bar", "Bas"], dict={'foo': "Bar"}, none=None, true=True, false=False)
        recurse_check_structure(sample, to_check)

    @raises(ValidationException)
    def test_recurse_check_structure_missingitem(self):
        sample = dict(string="Foobar", list=["Foo", "Bar"], dict={'foo': "Bar"}, none=None, true=True, false=False)
        to_check = dict(string="Foobar", list=["Foo", "Bar"], dict={'foo': "Bar"}, none=None, true=True)
        recurse_check_structure(sample, to_check)

    @raises(ValidationException)
    def test_recurse_check_structure_extrasubitem(self):
        sample = dict(string="Foobar", list=["Foo", "Bar"], dict={'foo': "Bar"}, none=None, true=True, false=False)
        to_check = dict(string="Foobar", list=["Foo", "Bar", "Bas"], dict={'foo': "Bar", 'Bar': "Foo"}, none=None, true=True, false=False)
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
