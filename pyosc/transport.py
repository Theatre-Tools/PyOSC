from enum import Enum
from typing import Protocol

from oscparser import OSCBundle, OSCMessage
from pydantic import BaseModel

from .dispatcher import Dispatcher


class ConnectionRole(Enum):
    INITIATING = "initiating"
    ACCEPTING = "accepting"


class Remote(BaseModel):
    address: str
    port: int


class Bind(BaseModel):
    bind_address: str
    bind_port: int


class Transport(Protocol):
    def send(self, packet: OSCMessage | OSCBundle): ...

    def receive(self) -> OSCMessage | OSCBundle: ...

    def start(self): ...

    def add_dispatcher(self, dispatcher: "Dispatcher"): ...
