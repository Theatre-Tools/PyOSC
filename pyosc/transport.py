from typing import Protocol

from oscparser import OSCBundle, OSCMessage
from pydantic import BaseModel

from .dispatcher import Dispatcher


class Remote(BaseModel):
    address: str
    port: int


class Transport(Protocol):
    def send(self, packet: OSCMessage | OSCBundle):
        ...

    def receive(self) -> OSCMessage | OSCBundle:
        ...

    def start(self):
        ...

    def add_dispatcher(self, dispatcher: 'Dispatcher'):
        ...
