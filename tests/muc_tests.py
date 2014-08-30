import errbot.backends.base
from errbot.backends.test import testbot
from errbot.plugin_manager import get_plugin_obj_by_name


class TestMUC(object):
    def test_plugin_methods(self, testbot):
        p = get_plugin_obj_by_name('ChatRoom')
        assert p is not None

        assert hasattr(p, 'rooms')
        assert hasattr(p, 'join_room')
        assert hasattr(p, 'leave_room')
        assert hasattr(p, 'get_room_topic')
        assert hasattr(p, 'set_room_topic')

    def test_join_leave_and_list(self, testbot):
        from errbot import holder
        rooms = holder.bot.rooms
        assert len(rooms) == 1
        assert rooms['err@conference.server.tld'].jid == 'err@conference.server.tld'
        assert issubclass(
            rooms['err@conference.server.tld'].__class__,
            errbot.backends.base.MUCRoom
        )

        holder.bot.join_room('room@conference.server.tld')
        assert 'room@conference.server.tld' in holder.bot.rooms

        holder.bot.leave_room('room@conference.server.tld')
        assert 'room@conference.server.tld' not in holder.bot.rooms

    def test_occupants(self, testbot):
        from errbot import holder
        room = holder.bot.rooms['err@conference.server.tld']
        assert 'err@localhost' in room.occupants.keys()

        assert issubclass(
            room.occupants['err@localhost'].__class__,
            errbot.backends.base.MUCOccupant
        )

    def test_topic(self, testbot):
        from errbot import holder
        room = holder.bot.rooms['err@conference.server.tld']
        assert room.topic is None
