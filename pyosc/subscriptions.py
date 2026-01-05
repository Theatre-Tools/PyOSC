from queue import Queue

from oscparser import OSCMessage

from pyosc.dispatcher import Dispatcher
from pyosc.peer import Peer


class Subscription:
    def __init__(
        self,
        peer: Peer,
        out_message: OSCMessage,
        in_address: str,
        dispatcher: Dispatcher,
        queue: Queue,
    ):
        self.peer = peer
        self.out_message = out_message
        self._in = in_address
        self.dispatcher = dispatcher
        self.queue = queue

    def subscribe(self):
        def handler(msg: OSCMessage):
            self.queue.put(msg)

        self.dispatcher.add_handler(self._in, handler)  # type: ignore
        self.peer.send_message(self.out_message)

    def unsubscribe(self):
        self.dispatcher.remove_handler(self._in)
        self.peer.send_message(self.out_message)
