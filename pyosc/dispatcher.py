from threading import Lock
from typing import Generic, Protocol, TypeVar, overload

from oscparser import OSCMessage
from pydantic import BaseModel, ValidationError


class DispatcherInterface[T: BaseModel](Protocol):
    def __call__(self, message: T) -> None: ...


T_C = TypeVar("T_C", bound=BaseModel, covariant=True)


class DispatcherController(Generic[T_C]):
    def __init__(
        self, dispatcher: "DispatcherInterface[T_C]", validator: type[T_C]
    ) -> None:
        self.dispatcher = dispatcher
        self.validator = validator

    def run(self, message: BaseModel):
        try:
            validated_message = self.validator.model_validate(message.model_dump())
            self.dispatcher(validated_message)
        except ValidationError:
            pass


class DispatchMatcher:
    def __init__(self, pattern: str) -> None:
        self.pattern = pattern

    def matches(self, address: str) -> bool:
        return self.pattern == address

    def __hash__(self) -> int:
        return hash(self.pattern)


class Dispatcher:
    """Dispatches incoming OSC messages to registered handlers based on their addresses."""

    def __init__(self):
        self.handlers: list[tuple[DispatchMatcher, DispatcherController[BaseModel]]] = (
            []
        )
        self.dispatch_cache: dict[str, tuple[DispatcherController[BaseModel], ...]] = {}
        self.dispatch_lock: Lock = Lock()

    @overload
    def add_handler(
        self, address: str, handler: DispatcherInterface[OSCMessage]
    ) -> None: ...

    @overload
    def add_handler[T: BaseModel](
        self, address: str, handler: DispatcherInterface[T], validator: type[T]
    ) -> None: ...

    def add_handler[T: BaseModel](
        self,
        address: str,
        handler: DispatcherInterface[T],
        validator: type[T] = OSCMessage,
    ):
        """
        Add a handler for a specific OSC address.
        - ``address``: The OSC address to handle.
        - ``handler``: A callable that takes an OSCMessage as its only argument.
        """
        matcher = DispatchMatcher(address)
        print(matcher.pattern)
        self.handlers.append((matcher, DispatcherController(handler, validator)))
        print(f"Added handler for address: {address}")
        print(self.handlers)

    def remove_handler(self, address: str):
        """
        Removes a handler for a specific OSC address.
        - ``address``: The OSC address to remove the handler for.
        """
        removed_handlers: list[
            tuple[DispatchMatcher, DispatcherController[BaseModel]]
        ] = []
        with self.dispatch_lock:
            for item in self.handlers:
                matcher, _ = item
                if matcher.pattern == address:
                    removed_handlers.append(item)
                    return

            for handler in removed_handlers:
                self.handlers.remove(handler)

            self.dispatch_cache = {}

    def dispatch(self, message: OSCMessage):
        """
        Dispatches an incoming OSC message to the appropriate handler based on its address.
        - ``message``: The incoming OSCMessage to dispatch.
        """

        with self.dispatch_lock:
            # print(message)
            with open("dispatch_log.txt", "a") as f:
                f.write(f"Dispatching message: {message.address}\n")

            with open("dispatch_cache.txt", "a") as f:
                f.write(f"Current dispatch cache: {self.dispatch_cache}\n")
            if message.address in self.dispatch_cache:
                for handler in self.dispatch_cache[message.address]:
                    handler.run(message)
                return

        matched_handlers: list[DispatcherController[BaseModel]] = []
        with self.dispatch_lock:
            # print(self.handlers)
            for matcher, handler in self.handlers:
                if matcher.matches(message.address):
                    matched_handlers.append(handler)
            self.dispatch_cache[message.address] = tuple(matched_handlers)

        for handler in matched_handlers:
            print(matched_handlers)
            handler.run(message)
