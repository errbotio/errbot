
from os import pipe, fdopen
from threading import Thread
from errbot.backends.base import (STREAM_WAITING_TO_START,
                                  STREAM_TRANSFER_IN_PROGRESS,
                                  STREAM_SUCCESSFULLY_TRANSFERED,
                                  STREAM_ERROR,
                                  STREAM_PAUSED,
                                  STREAM_REJECTED,)
import logging

CHUNK_SIZE = 4096


class Tee(object):
    """ Tee implements a multi reader / single writer """
    def __init__(self, incoming_stream, clients):
        """ clients is a list of objects implementing callback_stream """
        self.incoming_stream = incoming_stream
        self.clients = clients

    def start(self):
        """ starts the transfer asynchronously """
        t = Thread(target=self.run)
        t.start()
        return t

    def run(self):
        """ streams to all the clients synchronously """
        nb_clients = len(self.clients)
        pipes = [pipe() for i in range(nb_clients)]
        pipes = [(fdopen(r, 'rb'), fdopen(w, 'wb')) for r, w in pipes]
        streams = [self.incoming_stream.clone(pipe[0]) for pipe in pipes]

        def streamer(index):
            try:
                self.clients[index].callback_stream(streams[index])
                if streams[index].status == STREAM_WAITING_TO_START:
                    streams[index].reject()
                    logging.warning("%s did not accept nor reject the incoming file transfer, I reject it as a fallback." % self.clients[index].__class__.__name__)
            except Exception as _:
                # internal error, mark the error.
                streams[index].error()
            else:
                if streams[index].status == STREAM_TRANSFER_IN_PROGRESS:
                    # if the plugin didn't do it by itself, mark the transfer as a success.
                    streams[index].success()
            # stop the stream if the callback_stream returns
            r, w = pipes[index]
            pipes[index] = (None, None)  # signal the main thread to stop streaming
            r.close()
            w.close()

        threads = [Thread(target=streamer, args=(i,)) for i in range(nb_clients)]

        for thread in threads:
            thread.start()

        while True:
            if self.incoming_stream.closed:
                break
            chunk = self.incoming_stream.read(CHUNK_SIZE)
            logging.debug("dispatch %d bytes", len(chunk))
            if not chunk:
                break
            for (_, w) in pipes:
                if w:
                    w.write(chunk)
        logging.debug("EOF detected")
        for (r, w) in pipes:
            if w:
                w.close()  # close should flush too
        # we want to be sure that if we join on the main thread,
        # everything is either fully transfered or errored
        for thread in threads:
            thread.join()
