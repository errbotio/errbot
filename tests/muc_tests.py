import os
from queue import Empty
import errbot.backends.base
from errbot.backends.test import testbot, push_message, pop_message
from errbot.plugin_manager import get_plugin_obj_by_name


class TestMUC(object):
    extra_plugin_dir = os.path.dirname(os.path.realpath(__file__)) + os.sep + 'room_tests'

    def test_plugin_methods(self, testbot):
        p = get_plugin_obj_by_name('ChatRoom')
        assert p is not None

        assert hasattr(p, 'rooms')
        assert hasattr(p, 'query_room')

    def test_create_join_leave_destroy_lifecycle(self, testbot):
        from errbot import holder
        rooms = holder.bot.rooms()
        assert len(rooms) == 1

        r1 = rooms[0]
        assert str(r1) == "err@conference.server.tld"
        assert issubclass(r1.__class__, errbot.backends.base.MUCRoom)

        r2 = holder.bot.query_room('room@conference.server.tld')
        assert not r2.exists

        r2.create()
        assert r2.exists
        rooms = holder.bot.rooms()
        assert r2 not in rooms
        assert not r2.joined

        r2.destroy()
        rooms = holder.bot.rooms()
        assert r2 not in rooms

        r2.join()
        assert r2.exists
        assert r2.joined
        rooms = holder.bot.rooms()
        assert r2 in rooms

        r2 = holder.bot.query_room('room@conference.server.tld')
        assert r2.joined

        r2.leave()
        assert not r2.joined
        r2.destroy()
        rooms = holder.bot.rooms()
        assert r2 not in rooms

    def test_occupants(self, testbot):
        from errbot import holder
        room = holder.bot.rooms()[0]
        assert len(room.occupants) == 1
        assert 'err@localhost' in [str(o) for o in room.occupants]

        assert issubclass(
            room.occupants[0].__class__,
            errbot.backends.base.MUCOccupant
        )

    def test_topic(self, testbot):
        from errbot import holder
        room = holder.bot.rooms()[0]
        assert room.topic is None

        room.set_topic("Err rocks!")
        assert room.topic == "Err rocks!"
        assert holder.bot.rooms()[0].topic == "Err rocks!"

    def test_plugin_callbacks(self, testbot):
        p = get_plugin_obj_by_name('RoomTest')
        assert p is not None

        # Drains the event queue. `p.events.empty()` is unreliable.
        while True:
            try:
                p.events.get(timeout=5)
            except Empty:
                break

        p.query_room('newroom@conference.server.tld').join()
        assert p.events.get(timeout=5) == "callback_room_joined newroom@conference.server.tld"

        p.query_room('newroom@conference.server.tld').set_topic("Err rocks!")
        assert p.events.get(timeout=5) == "callback_room_topic Err rocks!"

        p.query_room('newroom@conference.server.tld').leave()
        assert p.events.get(timeout=5) == "callback_room_left newroom@conference.server.tld"

    def test_botcommands(self, testbot):
        from errbot import holder
        rooms = holder.bot.rooms()
        room = holder.bot.query_room('err@conference.server.tld')
        assert len(rooms) == 1
        assert rooms[0] == room

        assert room.joined
        push_message("!room leave err@conference.server.tld")
        assert pop_message() == "Left the room err@conference.server.tld"
        room = holder.bot.query_room('err@conference.server.tld')
        assert not room.joined

        push_message("!room list")
        assert pop_message() == "I'm not currently in any rooms."

        push_message("!room destroy err@conference.server.tld")
        assert pop_message() == "Destroyed the room err@conference.server.tld"
        rooms = holder.bot.rooms()
        room = holder.bot.query_room('err@conference.server.tld')
        assert not room.exists
        assert room not in rooms

        push_message("!room create err@conference.server.tld")
        assert pop_message() == "Created the room err@conference.server.tld"
        rooms = holder.bot.rooms()
        room = holder.bot.query_room('err@conference.server.tld')
        assert room.exists
        assert room not in rooms
        assert not room.joined

        push_message("!room join err@conference.server.tld")
        assert pop_message() == "Joined the room err@conference.server.tld"
        rooms = holder.bot.rooms()
        room = holder.bot.query_room('err@conference.server.tld')
        assert room.exists
        assert room.joined
        assert room in rooms

        push_message("!room list")
        assert pop_message() == "I'm currently in these rooms:\n\terr@conference.server.tld"

        push_message("!room occupants err@conference.server.tld")
        assert pop_message() == "Occupants in err@conference.server.tld:\n\terr@localhost"

        push_message("!room topic err@conference.server.tld")
        assert pop_message() == "No topic is set for err@conference.server.tld"
        push_message("!room topic err@conference.server.tld 'Err rocks!'")
        assert pop_message() == "Topic for err@conference.server.tld set."
        push_message("!room topic err@conference.server.tld")
        assert pop_message() == "Topic for err@conference.server.tld: Err rocks!"
