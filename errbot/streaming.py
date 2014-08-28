
from os import pipe, fdopen
from threading import Thread

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
            self.clients[index].callback_stream(streams[index])
            # stop the stream if the callback_stream returns
            r, w = pipes[index]
            pipes[index] = (None, None)  # signal the main thread to stop streaming
            r.close()
            w.close()

        threads = [Thread(target=streamer, args=(i,)) for i in range(nb_clients)]

        for thread in threads:
            thread.start()

        while True:
            chunk = self.incoming_stream.read(CHUNK_SIZE)
            if not chunk:
                break
            for (_, w) in pipes:
                if w:
                    w.write(chunk)
        for (r, w) in pipes:
            if w:
                w.close()  # close should flush too
        # we want to be sure that if we join on the main thread,
        # everything is either fully transfered or errored
        for thread in threads:
            thread.join()
