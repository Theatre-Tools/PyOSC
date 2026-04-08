import queue
import threading
from time import perf_counter_ns
from typing import overload

from oscparser import OSCMessage
from pydantic import BaseModel, ValidationError


class CallHandler_Response:
    def __init__(self, message: OSCMessage, latency: float):
        self.message = message
        self.latency = latency

class Call:
    def __init__[T: BaseModel](self, queue: queue.Queue[T], validator: type[T]):
        self.queue = queue
        self.validator = validator


class CallHandlerValidationError(ValueError):
    pass


class CallHandler:
    """"""

    def __init__(self, peer):
        self.peer = peer
        self.queues: dict[str, Call] = {}
        self.queue_lock = threading.Lock()

    @overload
    def call(
        self,
        message: OSCMessage,
        *,
        return_address: str | None = None,
        timeout: float = 5.0,
    ) -> CallHandler_Response | None: ...

    @overload
    def call[T: BaseModel](
        self,
        message: OSCMessage,
        *,
        return_address: str | None = None,
        validator: type[T],
        timeout: float = 5.0,
    ) -> CallHandler_Response | None: ...

    def call(
        self,
        message: OSCMessage,
        *,
        return_address: str | None = None,
        validator: type[BaseModel] | None = None,
        timeout: float = 5.0,
    ) -> CallHandler_Response | None:
        """Calling a call handler will send a message to the peer, and await a response that meets the critieria.

        Args:
            ``message (OSCMessage)``: An OSCMessage to send to the peer.
            ``return_address (str | None, optional)``: The address to listen for a response on. Defaults to None.
            ``validator (type[BaseModel] | None, optional)``: A Pydantic model to validate the response against. Defaults to None.
            ``timeout (float, optional)``: How long to wait for a response before timing out. Defaults to 5.0.

        Returns:
            - CallHandler_Response | None: A CallHandler_Response containing the response message and latency, or None if the call timed out.
        """

        if validator is None:
            validator = OSCMessage
        if not return_address:
            return_address = message.address
        responseq = queue.Queue()
        with self.queue_lock:
            self.queues[return_address] = Call(responseq, validator)
            handler = self.peer.register_handler(return_address, self)
        self.peer.send_message(message)
        start_time = perf_counter_ns()
        try:
            response = responseq.get(timeout=timeout)
            latency = perf_counter_ns() - start_time
            return CallHandler_Response(message=response, latency=latency / 1e9)
        except queue.Empty:
            return None
        finally:
            with self.queue_lock:
                handler.unregister()

    def __call__(self, message: OSCMessage):
        with self.queue_lock:
            if message.address in self.queues:
                try:
                    validated_msg = self.queues[message.address].validator.model_validate(message.model_dump())
                    self.queues[message.address].queue.put(validated_msg)
                except ValidationError as e:
                    raise CallHandlerValidationError(f"CallHandler validation error: {e}") from e
