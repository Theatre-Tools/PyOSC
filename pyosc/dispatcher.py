
from typing import Callable

from oscparser import OSCMessage

from .message import Message


class Dispatcher:
    """Dispatches incoming OSC messages to registered handlers based on their addresses."""

    def __init__(self):
        self.handlers = {}

    Handler = Callable[[OSCMessage], None]

    def add_handler(self, address: str, handler: Handler):
        """
        Add a handler for a specific OSC address.
        - ``address``: The OSC address to handle.
        - ``handler``: A callable that takes an OSCMessage as its only argument.
        """
        if address in self.handlers:
            raise ValueError(f"Handler already exists for address {address}")
        if address.endswith("/") and len(address) > 1:
            address = address[:-1]
        self.handlers[address] = handler

    def remove_handler(self, address: str):
        """
        Removes a handler for a specific OSC address.
        - ``address``: The OSC address to remove the handler for.
        """
        if address in self.handlers:
            del self.handlers[address]
        else:
            raise ValueError(f"No handler exists for address {address}")

    def add_default_handler(self, handler: Handler):
        """
        Adds a fallback default handler to any messages that don't have a specific handler assigned.
        - ``handler``: A callable that takes an OSCMessage as its only argument.
        """
        self.handlers[""] = handler

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
                self.handlers[addr_to_check](Message.from_message(message))
                return

