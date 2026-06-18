import socket

from oscparser import OSCTransport

from .exceptions import PeerConnectionError


def _initiate_tcp(self) -> socket.socket:
    try:
        tcp_connection = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        tcp_connection.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        tcp_connection.connect((self.remote_address, self.remote_port))
    except OSError as e:
        raise PeerConnectionError(f"Could not connect to TCP Peer at {self.remote_address}:{self.remote_port} - {e}") from e
    self._emit_connection_state(True)
    return tcp_connection


def _initiate_connection(self) -> socket.socket:
    if self.transport == OSCTransport.TCP:
        return _initiate_tcp(self)
    else:
        raise NotImplementedError("Only TCP initiator role is implemented")
