"""Tests for errbot.core internals."""
import logging

from errbot.core import ErrBot

extra_config = {"BOT_ADMINS_NOTIFICATIONS": "zoni@localdomain"}


def test_admins_to_notify(testbot):
    """Test which admins will be notified"""
    notified_admins = testbot._bot._admins_to_notify()
    assert "zoni@localdomain" in notified_admins


def test_admins_not_notified(testbot):
    """Test which admins will not be notified"""
    notified_admins = testbot._bot._admins_to_notify()
    assert "gbin@local" not in notified_admins


# --- _process_command_filters --------------------------------------------
# Regression tests for PR #1631: when a cmdfilter blocks a command by
# returning ``(None, cmd, args)``, the command name must propagate back to
# the caller so it can be logged instead of "None".


class _FilterStub:
    """Minimal stand-in for an ErrBot exposing only what
    ``_process_command_filters`` touches: a ``command_filters`` list."""

    def __init__(self, filters):
        self.command_filters = filters


def _block_filter(msg, cmd, args, dry_run):
    return None, cmd, args


def _passthrough_filter(msg, cmd, args, dry_run):
    return msg, cmd, args


def _raising_filter(msg, cmd, args, dry_run):
    raise RuntimeError("boom")


def test_blocked_command_preserves_cmd_and_args():
    stub = _FilterStub([_block_filter])
    msg, cmd, args = ErrBot._process_command_filters(
        stub, msg="hello", cmd="mycmd", args=("a", "b")
    )
    assert msg is None
    assert cmd == "mycmd"
    assert args == ("a", "b")


def test_passthrough_filter_returns_unchanged():
    stub = _FilterStub([_passthrough_filter])
    msg, cmd, args = ErrBot._process_command_filters(
        stub, msg="hello", cmd="mycmd", args=("a",)
    )
    assert msg == "hello"
    assert cmd == "mycmd"
    assert args == ("a",)


def test_raising_filter_blocks_with_none_tuple():
    stub = _FilterStub([_raising_filter])
    msg, cmd, args = ErrBot._process_command_filters(
        stub, msg="hello", cmd="mycmd", args=("a",)
    )
    assert (msg, cmd, args) == (None, None, None)


def test_blocked_command_logs_cmd_name(caplog):
    stub = _FilterStub([_block_filter])
    with caplog.at_level(logging.INFO, logger="errbot.core"):
        msg, cmd, args = ErrBot._process_command_filters(
            stub, msg="hello", cmd="mycmd", args=()
        )
    assert msg is None
    assert cmd == "mycmd"
