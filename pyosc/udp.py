import socket
from typing import TYPE_CHECKING

from .exceptions import PeerConfigurationError

if TYPE_CHECKING:
    from pyosc.peer import Peer


def _begin_udp(self: Peer) -> socket.socket:
    if self.connection_role:
        raise PeerConfigurationError("UDP Peers cannot have a connection role assigned")
    try:
        if self.bind_address is None:
            raise PeerConfigurationError("UDP bind address must be specified for UDP Peers")
        if self.bind_port is None:
            raise PeerConfigurationError("Bind port must be specified for UDP Peers")
        udp_connection = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        udp_connection.bind((self.bind_address, self.bind_port))
    except OSError as e:
        raise PeerConfigurationError(f"Could not bind UDP Peer to {self.bind_address}:{self.bind_port} - {e}") from e
    self._emit_connection_state(True)
    return udp_connection
