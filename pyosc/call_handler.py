import queue
import threading
from typing import overload

from oscparser import OSCMessage
from pydantic import BaseModel, ValidationError

from pyosc.peer import Peer


class Call:
    def __init__[T: BaseModel](self, queue: queue.Queue[T], validator: type[T]):
        self.queue = queue
        self.validator = validator


class CallHandler:
    """A call handler is a way of communicating with a peer that is more akin to a restuful API from the user point of view. You send a request, it gives you a response."""

    def __init__(self, peer: Peer):
        self.peer = peer
        self.queues: dict[str, Call] = {}
        self.queue_lock = threading.Lock()

    @overload
    def call(self, msg: OSCMessage, *, return_addr: str | None = None, timeout: float = 5.0) -> OSCMessage | None: ...

    @overload
    def call[T: BaseModel](
        self,
        msg: OSCMessage,
        *,
        return_addr: str | None = None,
        validator: type[T],
        timeout: float = 5.0,
    ) -> T | None: ...

    def call(
        self,
        msg: OSCMessage,
        *,
        return_addr: str | None = None,
        validator: type[BaseModel] | None = None,
        timeout: float = 5.0,
    ) -> BaseModel | None:
        """Calling a call handler will send a message to the peer, and await a response that meets the critieria.

        Args:
            ``msg (OSCMessage)``: An OSCMessage to send to the peer.
            ``return_addr (str | None, optional)``: The address to listen for a response on. Defaults to None.
            ``validator (type[BaseModel] | None, optional)``: A Pydantic model to validate the response against. Defaults to None.
            ``timeout (float, optional)``: How long to wait for a response before timing out. Defaults to 5.0.

        Returns:
            BaseModel | None: The validated response model if received within the timeout period, otherwise None.
        """
        if validator is None:
            validator = OSCMessage
        if not return_addr:
            return_addr = msg.address
        responseq = queue.Queue()
        with self.queue_lock:
            self.queues[return_addr] = Call(responseq, validator)
        self.peer.send_message(msg)
        try:
            response = responseq.get(timeout=timeout)
            return response
        except queue.Empty:
            with self.queue_lock:
                del self.queues[return_addr]
            return None

    def __call__(self, msg: OSCMessage):
        with self.queue_lock:
            if msg.address in self.queues:
                try:
                    validated_msg = self.queues[msg.address].validator.model_validate(msg.model_dump())
                    self.queues[msg.address].queue.put(validated_msg)
                except ValidationError as e:
                    print("CallHandler validation error:", e)
        # print("CallHandler received message:", msg.address, msg.args)
