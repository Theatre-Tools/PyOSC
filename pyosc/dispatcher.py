from typing import Generic, Protocol, TypeVar, overload

from oscparser import OSCMessage
from pydantic import BaseModel, ValidationError


class DispatcherInterface[T: BaseModel](Protocol):
    def __call__(self, message: T) -> None:
        ...

T_C = TypeVar("T_C", bound=BaseModel, covariant=True)

class DispatcherControler(Generic[T_C]):
    def __init__(self, dispatcher: "DispatcherInterface[T_C]", validator: type[T_C]) -> None:
        self.dispatcher = dispatcher
        self.validator = validator

    def run(self, message: BaseModel):
        try:
            validated_message = self.validator.model_validate(message.model_dump())
            self.dispatcher(validated_message)
        except ValidationError:
            pass

class Dispatcher:
    """Dispatches incoming OSC messages to registered handlers based on their addresses."""

    def __init__(self):
        self.handlers: dict[str, DispatcherControler[BaseModel]] = {}

    @overload
    def add_handler(self, address: str, handler: DispatcherInterface[OSCMessage]) -> None: ...

    @overload
    def add_handler[T: BaseModel](self, address: str, handler: DispatcherInterface[T], validator: type[T]) -> None: ...

    def add_handler[T: BaseModel](self, address: str, handler: DispatcherInterface[T], validator: type[T] = OSCMessage):
        """
        Add a handler for a specific OSC address.
        - ``address``: The OSC address to handle.
        - ``handler``: A callable that takes an OSCMessage as its only argument.
        """
        if address in self.handlers:
            raise ValueError(f"Handler already exists for address {address}")
        if address.endswith("/") and len(address) > 1:
            address = address[:-1]
        self.handlers[address] = DispatcherControler(handler, validator)

    def remove_handler(self, address: str):
        """
        Removes a handler for a specific OSC address.
        - ``address``: The OSC address to remove the handler for.
        """
        if address in self.handlers:
            del self.handlers[address]
        else:
            raise ValueError(f"No handler exists for address {address}")

    def add_default_handler(self, handler: DispatcherInterface[OSCMessage]):
        """
        Adds a fallback default handler to any messages that don't have a specific handler assigned.
        - ``handler``: A callable that takes an OSCMessage as its only argument.
        """
        self.handlers[""] = DispatcherControler(handler, OSCMessage)

    def dispatch(self, message: OSCMessage):
        """
        Dispatches an incoming OSC message to the appropriate handler based on its address.
        - ``message``: The incoming OSCMessage to dispatch.
        """
        ## Split the address into it's parts
        ## This allows us to iterate over every part of it in order to match wildcards and less specific addresses
        parts = message.address.split("/")
        for i in range(len(parts), 0, -1):
            addr_to_check = "/".join(parts[:i])
            if addr_to_check in self.handlers:
                self.handlers[addr_to_check].run(message)
                return
