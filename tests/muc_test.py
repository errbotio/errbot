import logging
import os

import errbot.backends.base
from errbot.backends.test import TestOccupant

log = logging.getLogger(__name__)

extra_plugin_dir = os.path.join(
    os.path.dirname(os.path.realpath(__file__)), "room_plugin"
)


def test_plugin_methods(testbot):
    p = testbot.bot.plugin_manager.get_plugin_obj_by_name("ChatRoom")
    assert p is not None

    assert hasattr(p, "rooms")
    assert hasattr(p, "query_room")


def test_create_join_leave_destroy_lifecycle(testbot):  # noqa
    rooms = testbot.bot.rooms()
    assert len(rooms) == 1

    r1 = rooms[0]
    assert str(r1) == "testroom"
    assert issubclass(r1.__class__, errbot.backends.base.Room)

    r2 = testbot.bot.query_room("testroom2")
    assert not r2.exists

    r2.create()
    assert r2.exists
    rooms = testbot.bot.rooms()
    assert r2 not in rooms
    assert not r2.joined

    r2.destroy()
    rooms = testbot.bot.rooms()
    assert r2 not in rooms

    r2.join()
    assert r2.exists
    assert r2.joined
    rooms = testbot.bot.rooms()
    assert r2 in rooms

    r2 = testbot.bot.query_room("testroom2")
    assert r2.joined

    r2.leave()
    assert not r2.joined
    r2.destroy()
    rooms = testbot.bot.rooms()
    assert r2 not in rooms


def test_occupants(testbot):  # noqa
    room = testbot.bot.rooms()[0]
    assert len(room.occupants) == 1
    assert TestOccupant("err", "testroom") in room.occupants


def test_topic(testbot):  # noqa
    room = testbot.bot.rooms()[0]
    assert room.topic is None

    room.topic = "Errbot rocks!"
    assert room.topic == "Errbot rocks!"
    assert testbot.bot.rooms()[0].topic == "Errbot rocks!"


def test_plugin_callbacks(testbot):  # noqa
    p = testbot.bot.plugin_manager.get_plugin_obj_by_name("RoomTest")
    assert p is not None
    p.purge()

    log.debug("query and join")
    p.query_room("newroom").join()
    assert p.events.get(timeout=5) == "callback_room_joined newroom"

    p.query_room("newroom").topic = "Errbot rocks!"
    assert p.events.get(timeout=5) == "callback_room_topic Errbot rocks!"

    p.query_room("newroom").leave()
    assert p.events.get(timeout=5) == "callback_room_left newroom"


def test_botcommands(testbot):  # noqa
    rooms = testbot.bot.rooms()
    room = testbot.bot.query_room("testroom")
    assert len(rooms) == 1
    assert rooms[0] == room

    assert room.joined
    assert "Left the room testroom" in testbot.exec_command("!room leave testroom")
    room = testbot.bot.query_room("testroom")
    assert not room.joined

    assert "I'm not currently in any rooms." in testbot.exec_command("!room list")

    assert "Destroyed the room testroom" in testbot.exec_command(
        "!room destroy testroom"
    )

    rooms = testbot.bot.rooms()
    room = testbot.bot.query_room("testroom")
    assert not room.exists
    assert room not in rooms

    assert "Created the room testroom" in testbot.exec_command("!room create testroom")
    rooms = testbot.bot.rooms()
    room = testbot.bot.query_room("testroom")
    assert room.exists
    assert room not in rooms
    assert not room.joined

    assert "Joined the room testroom" in testbot.exec_command("!room join testroom")
    rooms = testbot.bot.rooms()
    room = testbot.bot.query_room("testroom")
    assert room.exists
    assert room.joined
    assert room in rooms

    assert "Created the room testroom with spaces" in testbot.exec_command(
        "!room create 'testroom with spaces'"
    )
    rooms = testbot.bot.rooms()
    room = testbot.bot.query_room("testroom with spaces")
    assert room.exists
    assert room not in rooms
    assert not room.joined

    assert "Joined the room testroom with spaces" in testbot.exec_command(
        "!room join 'testroom with spaces'"
    )
    rooms = testbot.bot.rooms()
    room = testbot.bot.query_room("testroom with spaces")
    assert room.exists
    assert room.joined
    assert room in rooms

    assert "testroom" in testbot.exec_command("!room list")
    assert "err" in testbot.exec_command("!room occupants testroom")
    assert "No topic is set for testroom" in testbot.exec_command(
        "!room topic testroom"
    )
    assert "Topic for testroom set." in testbot.exec_command(
        "!room topic testroom 'Errbot rocks!'"
    )
    assert "Topic for testroom: Errbot rocks!" in testbot.exec_command(
        "!room topic testroom"
    )
