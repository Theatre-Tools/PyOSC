import queue
import re
import threading
from time import perf_counter_ns
from typing import Any, overload

from oscparser import OSCMessage
from pydantic import BaseModel, ValidationError

from .exceptions import CallHandlerValidationError


class CallHandler_Response[T: BaseModel]:
    def __init__(self, message: T, latency: float):
        self.message = message
        self.latency = latency


class Call:
    def __init__[T: BaseModel](self, queue: queue.Queue[T], validator: type[T]):
        self.queue = queue
        self.validator = validator


class CallHandler:
    def __init__(self, peer):
        self.peer = peer
        self.queues: dict[re.Pattern, Call] = {}
        self.queue_lock = threading.Lock()

    @overload
    def call(
        self,
        message: OSCMessage,
        *,
        message_return_address: str | None = None,
        timeout: float = 5.0,
        max_responses: int = 1,
    ) -> CallHandler_Response[OSCMessage] | list[CallHandler_Response[OSCMessage]] | None: ...

    @overload
    def call[T: BaseModel](
        self,
        message: OSCMessage,
        *,
        message_return_address: str | None = None,
        validator: type[T],
        timeout: float = 5.0,
        max_responses: int = 1,
    ) -> CallHandler_Response[T] | list[CallHandler_Response[T]] | None: ...

    def call(
        self,
        message: OSCMessage,
        *,
        message_return_address: str | None = None,
        validator: type[BaseModel] | None = None,
        timeout: float = 5.0,
        max_responses: int = 1,
    ) -> CallHandler_Response[Any] | list[CallHandler_Response[Any]] | None:
        """Calling a call handler will send a message to the peer, and await a response that meets the critieria.

        Args:
            ``message (OSCMessage)``: An OSCMessage to send to the peer.
            ``message_return_address (str | None, optional)``: The address to listen for a response on. Defaults to None.
            ``validator (type[BaseModel] | None, optional)``: A Pydantic model to validate the response against. Defaults to None.
            ``timeout (float, optional)``: How long to wait for a response before timing out. Defaults to 5.0.
            ``max_responses (int, optional)``: How many responses to wait for before returning. Defaults to 1.
        Returns:
            - CallHandler_Response | list[CallHandler_Response] | None: A CallHandler_Response or list of CallHandler_Responses containing the response messages and latencies, or None if the call timed out.
        """

        if validator is None:
            validator = OSCMessage
        if not message_return_address:
            message_return_address = message.address
        responseq = queue.Queue()
        with self.queue_lock:
            handler = self.peer.register_handler(message_return_address, self)
            self.queues[handler.pattern] = Call(responseq, validator)
        start_time = perf_counter_ns()
        try:
            self.peer.send_message(message)
            if max_responses > 1:
                response_list = []
                for i in range(max_responses):
                    try:
                        latency = perf_counter_ns() - start_time
                        response_list.append(
                            CallHandler_Response(
                                message=responseq.get(timeout=timeout),
                                latency=latency / 1e6,
                            )
                        )
                    except queue.Empty:
                        if response_list:
                            return response_list
                        else:
                            return None
                return response_list
            else:
                response = responseq.get(timeout=timeout)
                latency = perf_counter_ns() - start_time
                return CallHandler_Response(message=response, latency=latency / 1e6)
        except queue.Empty:
            return None
        finally:
            with self.queue_lock:
                self.queues.pop(handler.pattern, None)
                handler.unregister()

    def __call__(self, message: OSCMessage):
        with self.queue_lock:
            for pattern in self.queues.items():
                if isinstance(pattern[0], re.Pattern) and pattern[0].fullmatch(message.address):
                    break
            else:
                return
            call = self.queues.get(pattern[0])
            if call is None:
                return

            try:
                call.queue.put(call.validator.model_validate(message.model_dump()))
            except ValidationError as e:
                raise CallHandlerValidationError(f"CallHandler validation error: {e}") from e
