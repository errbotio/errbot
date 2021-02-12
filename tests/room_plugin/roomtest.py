import logging
from queue import Queue

from errbot import BotPlugin

log = logging.getLogger(__name__)


class RoomTest(BotPlugin):
    def activate(self):
        super().activate()
        self.purge()

    def callback_room_joined(self, room, user, invited_by):
        log.info("join")
        self.events.put("callback_room_joined {!s}".format(room))

    def callback_room_left(self, room, user, kicked_by):
        self.events.put("callback_room_left {!s}".format(room))

    def callback_room_topic(self, room):
        self.events.put("callback_room_topic {}".format(room.topic))

    def purge(self):
        log.info("purge")
        self.events = Queue()
