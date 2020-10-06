from os import path
from errbot.botplugin import recurse_check_structure, ValidationException
import pytest

extra_plugin_dir = path.join(path.dirname(path.realpath(__file__)), "config_plugin")


def test_recurse_check_structure_valid():
    sample = dict(
        string="Foobar",
        list=["Foo", "Bar"],
        dict={"foo": "Bar"},
        none=None,
        true=True,
        false=False,
    )
    to_check = dict(
        string="Foobar",
        list=["Foo", "Bar", "Bas"],
        dict={"foo": "Bar"},
        none=None,
        true=True,
        false=False,
    )
    recurse_check_structure(sample, to_check)


def test_recurse_check_structure_missingitem():
    sample = dict(
        string="Foobar",
        list=["Foo", "Bar"],
        dict={"foo": "Bar"},
        none=None,
        true=True,
        false=False,
    )
    to_check = dict(
        string="Foobar", list=["Foo", "Bar"], dict={"foo": "Bar"}, none=None, true=True
    )
    with pytest.raises(ValidationException):
        recurse_check_structure(sample, to_check)


def test_recurse_check_structure_extrasubitem():
    sample = dict(
        string="Foobar",
        list=["Foo", "Bar"],
        dict={"foo": "Bar"},
        none=None,
        true=True,
        false=False,
    )
    to_check = dict(
        string="Foobar",
        list=["Foo", "Bar", "Bas"],
        dict={"foo": "Bar", "Bar": "Foo"},
        none=None,
        true=True,
        false=False,
    )
    with pytest.raises(ValidationException):
        recurse_check_structure(sample, to_check)


def test_recurse_check_structure_missingsubitem():
    sample = dict(
        string="Foobar",
        list=["Foo", "Bar"],
        dict={"foo": "Bar"},
        none=None,
        true=True,
        false=False,
    )
    to_check = dict(
        string="Foobar",
        list=["Foo", "Bar", "Bas"],
        dict={},
        none=None,
        true=True,
        false=False,
    )
    with pytest.raises(ValidationException):
        recurse_check_structure(sample, to_check)


def test_recurse_check_structure_wrongtype_1():
    sample = dict(
        string="Foobar",
        list=["Foo", "Bar"],
        dict={"foo": "Bar"},
        none=None,
        true=True,
        false=False,
    )
    to_check = dict(
        string=None,
        list=["Foo", "Bar"],
        dict={"foo": "Bar"},
        none=None,
        true=True,
        false=False,
    )
    with pytest.raises(ValidationException):
        recurse_check_structure(sample, to_check)


def test_recurse_check_structure_wrongtype_2():
    sample = dict(
        string="Foobar",
        list=["Foo", "Bar"],
        dict={"foo": "Bar"},
        none=None,
        true=True,
        false=False,
    )
    to_check = dict(
        string="Foobar",
        list={"foo": "Bar"},
        dict={"foo": "Bar"},
        none=None,
        true=True,
        false=False,
    )
    with pytest.raises(ValidationException):
        recurse_check_structure(sample, to_check)


def test_recurse_check_structure_wrongtype_3():
    sample = dict(
        string="Foobar",
        list=["Foo", "Bar"],
        dict={"foo": "Bar"},
        none=None,
        true=True,
        false=False,
    )
    to_check = dict(
        string="Foobar",
        list=["Foo", "Bar"],
        dict=["Foo", "Bar"],
        none=None,
        true=True,
        false=False,
    )
    with pytest.raises(ValidationException):
        recurse_check_structure(sample, to_check)


def test_failed_config(testbot):
    assert "Plugin configuration done." in testbot.exec_command(
        '!plugin config Config {"One": "two"}'
    )
