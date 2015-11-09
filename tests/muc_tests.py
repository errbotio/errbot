import os
import errbot.backends.base
from errbot.backends.test import FullStackTest, TestMUCOccupant
import logging
import unittest
log = logging.getLogger(__name__)


class TestMUC(FullStackTest):

    def setUp(self, extra_plugin_dir=None, extra_test_file=None, loglevel=logging.DEBUG):
        super().setUp(os.path.join(os.path.dirname(os.path.realpath(__file__)), 'room_tests'),
                      extra_test_file)

    def test_plugin_methods(self):  # noqa
        p = self.bot.get_plugin_obj_by_name('ChatRoom')
        assert p is not None

        assert hasattr(p, 'rooms')
        assert hasattr(p, 'query_room')

    def test_create_join_leave_destroy_lifecycle(self):  # noqa
        rooms = self.bot.rooms()
        assert len(rooms) == 1

        r1 = rooms[0]
        assert str(r1) == "testroom"
        assert issubclass(r1.__class__, errbot.backends.base.MUCRoom)

        r2 = self.bot.query_room('testroom2')
        assert not r2.exists

        r2.create()
        assert r2.exists
        rooms = self.bot.rooms()
        assert r2 not in rooms
        assert not r2.joined

        r2.destroy()
        rooms = self.bot.rooms()
        assert r2 not in rooms

        r2.join()
        assert r2.exists
        assert r2.joined
        rooms = self.bot.rooms()
        assert r2 in rooms

        r2 = self.bot.query_room('testroom2')
        assert r2.joined

        r2.leave()
        assert not r2.joined
        r2.destroy()
        rooms = self.bot.rooms()
        assert r2 not in rooms

    def test_occupants(self):  # noqa
        room = self.bot.rooms()[0]
        assert len(room.occupants) == 1
        assert TestMUCOccupant('err', 'testroom') in room.occupants

    def test_topic(self):  # noqa
        room = self.bot.rooms()[0]
        assert room.topic is None

        room.topic = "Err rocks!"
        assert room.topic == "Err rocks!"
        assert self.bot.rooms()[0].topic == "Err rocks!"

    def test_plugin_callbacks(self):  # noqa
        p = self.bot.get_plugin_obj_by_name('RoomTest')
        assert p is not None
        p.purge()

        log.debug("query and join")
        p.query_room('newroom').join()
        assert p.events.get(timeout=5) == "callback_room_joined newroom"

        p.query_room('newroom').topic = "Err rocks!"
        assert p.events.get(timeout=5) == "callback_room_topic Err rocks!"

        p.query_room('newroom').leave()
        assert p.events.get(timeout=5) == "callback_room_left newroom"

    def test_botcommands(self):  # noqa
        rooms = self.bot.rooms()
        room = self.bot.query_room('testroom')
        assert len(rooms) == 1
        assert rooms[0] == room

        assert room.joined
        self.bot.push_message("!room leave testroom")
        assert self.bot.pop_message() == "Left the room testroom"
        room = self.bot.query_room('testroom')
        assert not room.joined

        self.bot.push_message("!room list")
        assert self.bot.pop_message() == "I'm not currently in any rooms."

        self.bot.push_message("!room destroy testroom")
        assert self.bot.pop_message() == "Destroyed the room testroom"
        rooms = self.bot.rooms()
        room = self.bot.query_room('testroom')
        assert not room.exists
        assert room not in rooms

        self.bot.push_message("!room create testroom")
        assert self.bot.pop_message() == "Created the room testroom"
        rooms = self.bot.rooms()
        room = self.bot.query_room('testroom')
        assert room.exists
        assert room not in rooms
        assert not room.joined

        self.bot.push_message("!room join testroom")
        assert self.bot.pop_message() == "Joined the room testroom"
        rooms = self.bot.rooms()
        room = self.bot.query_room('testroom')
        assert room.exists
        assert room.joined
        assert room in rooms

        self.bot.push_message("!room list")
        assert "testroom" in self.bot.pop_message()

        self.bot.push_message("!room occupants testroom")
        assert "err" in self.bot.pop_message()

        self.bot.push_message("!room topic testroom")
        assert self.bot.pop_message() == "No topic is set for testroom"
        self.bot.push_message("!room topic testroom 'Err rocks!'")
        assert self.bot.pop_message() == "Topic for testroom set."
        self.bot.push_message("!room topic testroom")
        assert self.bot.pop_message() == "Topic for testroom: Err rocks!"
