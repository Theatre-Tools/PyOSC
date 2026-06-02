import socket

from oscparser import OSCTransport

from .exceptions import PeerConfigurationError, PeerConnectionError


def _initiate_tcp(self) -> socket.socket:
    try:
        tcp_connection = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        tcp_connection.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        tcp_connection.connect((self.address, self.port))
    except OSError as e:
        raise PeerConnectionError(
            f"Could not connect to TCP Peer at {self.address}:{self.port} - {e}"
        ) from e
    self._emit_connection_state(True)
    return tcp_connection


def _initiate_udp(self) -> socket.socket:
    try:
        if self.udp_rx_address is None:
            raise PeerConfigurationError(
                "UDP RX address must be specified for UDP Peers"
            )
        if self.udp_rx_port is None:
            raise PeerConfigurationError("UDP RX port must be specified for UDP Peers")
        udp_connection = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        udp_connection.bind((self.udp_rx_address, self.udp_rx_port))
    except OSError as e:
        raise PeerConnectionError(
            f"Could not bind UDP Peer at localhost:{self.udp_rx_port} - {e}"
        ) from e
    self._emit_connection_state(True)
    return udp_connection


def _initiate_connection(self) -> socket.socket:
    if self.transport == OSCTransport.TCP:
        return _initiate_tcp(self)

    else:
        return _initiate_udp(self)

