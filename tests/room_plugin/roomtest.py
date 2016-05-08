from errbot import BotPlugin
from queue import Queue
import logging
log = logging.getLogger(__name__)


class RoomTest(BotPlugin):

    def activate(self):
        super().activate()
        self.purge()

    def callback_room_joined(self, room):
        log.info("join")
        self.events.put("callback_room_joined {!s}".format(room))

    def callback_room_left(self, room):
        self.events.put("callback_room_left {!s}".format(room))

    def callback_room_topic(self, room):
        self.events.put("callback_room_topic {}".format(room.topic))

    def purge(self):
        log.info("purge")
        self.events = Queue()
