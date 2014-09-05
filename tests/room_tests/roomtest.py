from errbot import BotPlugin
from queue import Queue


class RoomTest(BotPlugin):
    def __init__(self):
        super(RoomTest, self).__init__()
        self.events = Queue()

    def callback_room_joined(self, room):
        self.events.put("callback_room_joined {!s}".format(room))

    def callback_room_left(self, room):
        self.events.put("callback_room_left {!s}".format(room))

    def callback_room_topic(self, room):
        self.events.put("callback_room_topic {}".format(room.topic))
