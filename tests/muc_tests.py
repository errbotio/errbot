import pytest
import errbot.backends.base
from errbot.backends.test import testbot
from errbot.plugin_manager import get_plugin_obj_by_name


class TestMUC(object):
    def test_plugin_methods(self, testbot):
        p = get_plugin_obj_by_name('ChatRoom')
        assert p is not None

        assert hasattr(p, 'rooms')
        assert hasattr(p, 'query_room')

    def test_create_join_leave_destroy_lifecycle(self, testbot):
        from errbot import holder
        rooms = holder.bot.rooms
        assert len(rooms) == 1

        r1 = rooms[0]
        assert str(r1) == "err@conference.server.tld"
        assert issubclass(r1.__class__, errbot.backends.base.MUCRoom)

        r2 = holder.bot.query_room('room@conference.server.tld')
        assert not r2.exists

        r2.create()
        assert r2.exists
        rooms = holder.bot.rooms
        assert r2 in rooms
        assert not r2.joined

        r2.destroy()
        rooms = holder.bot.rooms
        assert r2 not in rooms

        r2.join()
        assert r2.exists
        assert r2.joined
        rooms = holder.bot.rooms
        assert r2 in rooms

        r2 = holder.bot.query_room('room@conference.server.tld')
        assert r2.joined

        r2.leave()
        assert not r2.joined
        r2.destroy()
        rooms = holder.bot.rooms
        assert r2 not in rooms

    def test_occupants(self, testbot):
        from errbot import holder
        room = holder.bot.rooms[0]
        assert len(room.occupants) == 1
        assert 'err@localhost' in [str(o) for o in room.occupants]

        assert issubclass(
            room.occupants[0].__class__,
            errbot.backends.base.MUCOccupant
        )

    def test_topic(self, testbot):
        from errbot import holder
        room = holder.bot.rooms[0]
        assert room.topic is None

        room.topic = "Err rocks!"
        assert room.topic == "Err rocks!"
        assert holder.bot.rooms[0].topic == "Err rocks!"
