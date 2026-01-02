import queue
import threading
from typing import overload

from oscparser import OSCMessage
from pydantic import BaseModel, ValidationError

from .peer import Peer


class Call:
    def __init__[T: BaseModel](self, queue: queue.Queue[T], validator: type[T]):
        self.queue = queue
        self.validator = validator

class CallHandler:
    def __init__(self, peer: Peer):
        self.peer = peer
        self.queues: dict[str, Call] = {}
        self.queue_lock = threading.Lock()

    @overload
    def call(
        self, msg: OSCMessage, *, return_addr: str | None = None, timeout: float = 5.0
    ) -> OSCMessage | None: ...

    @overload
    def call[T: BaseModel](
        self, msg: OSCMessage, *, return_addr: str | None = None, validator: type[T], timeout: float = 5.0
    ) -> T | None: ...

    def call(
        self, msg: OSCMessage, *, return_addr: str | None = None, validator: type[BaseModel] | None = None,  timeout: float = 5.0
    ) -> BaseModel | None:
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
