from enum import Enum
from typing import TYPE_CHECKING, Protocol

from oscparser import OSCBundle, OSCMessage, OSCTransport
from pydantic import BaseModel

if TYPE_CHECKING:
    from .peer import Peer


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
    @staticmethod
    def from_peer(peer: "Peer") -> "Transport":
        if peer.transport == OSCTransport.UDP:
            from .udp import UDPTransport

            return UDPTransport.create_from_peer(peer)
        elif peer.transport == OSCTransport.TCP:
            from .tcp import TCPTransport

            return TCPTransport.create_from_peer(peer)
        else:
            raise ValueError(f"Unsupported transport type: {peer.transport}")

    def send(self, packet: OSCMessage | OSCBundle): ...

    def listen(self): ...

    def close(self): ...
