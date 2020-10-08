from io import BytesIO

from errbot.backends.base import Stream
from errbot.backends.test import TestPerson
from errbot.streaming import Tee


class StreamingClient(object):
    def callback_stream(self, stream):
        self.response = stream.read()


def test_streaming():
    canary = b"this is my test" * 1000
    source = Stream(TestPerson("gbin@gootz.net"), BytesIO(canary))
    clients = [StreamingClient() for _ in range(50)]
    Tee(source, clients).run()
    for client in clients:
        assert client.response == canary
