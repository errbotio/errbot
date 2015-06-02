import unittest
from io import BytesIO
from errbot.streaming import Tee
from errbot.backends.base import Stream
from errbot.backends.text import SimpleIdentifier
import logging


class StreamingClient(object):
    def callback_stream(self, stream):
        self.response = stream.read()


def test_streaming():
    canary = b'this is my test' * 1000
    source = Stream(SimpleIdentifier("gbin@gootz.net"), BytesIO(canary))
    clients = [StreamingClient() for i in range(50)]
    Tee(source, clients).run()
    for client in clients:
        assert client.response == canary
