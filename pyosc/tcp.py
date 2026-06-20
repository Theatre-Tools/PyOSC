import socket
import threading
from dataclasses import dataclass
from select import select
from typing import TYPE_CHECKING, Optional

from oscparser import OSCDecoder, OSCEncoder, OSCFraming, OSCTransport

from .exceptions import PeerConnectionError, PeerListenerError
from .transport import Bind, ConnectionRole, Remote, Transport

if TYPE_CHECKING:
    from .peer import Peer


@dataclass
class connectionFamily:
    connection: Optional[socket.socket] = None
    binding: Optional[socket.socket] = None

    def graceful_close(self):
        for sock in (self.connection, self.binding):
            if sock:
                try:
                    sock.shutdown(socket.SHUT_RDWR)
                except OSError:
                    pass

                sock.close()
                sock = None


@dataclass
class threadFamily:
    _acceptance_thread: Optional[threading.Thread] = None
    _listener_thread: Optional[threading.Thread] = None
    _bind_thread: Optional[threading.Thread] = None

    def graceful_close(self):

        for thread in (self._acceptance_thread, self._listener_thread, self._bind_thread):
            if thread and thread.is_alive():
                thread.join(timeout=1)


class TCPTransport(Transport):
    def __init__(
        self,
        framing: OSCFraming,
        peer: "Peer",
        connection_role: ConnectionRole = ConnectionRole.INITIATING,
        remote: Optional[Remote] = None,
        bind: Optional[Bind] = None,
    ):
        self.connection_role = connection_role
        self.framing = framing
        self.peer = peer
        self.encoder = OSCEncoder(transport=OSCTransport.TCP, framing=framing)
        self.decoder = OSCDecoder(transport=OSCTransport.TCP, framing=framing)
        self.threads = threadFamily()
        self.connection: connectionFamily = connectionFamily()

        if connection_role == ConnectionRole.INITIATING:
            if remote is None:
                raise ValueError("Remote peer must be provided for initiating connection")
            self.remote = remote
        else:
            if bind is None:
                raise ValueError("Bind interface must be provided for accepting connection")
            self.bind = bind
            self.remote = remote

    @classmethod
    def from_peer(cls, peer: "Peer") -> "TCPTransport":
        if (
            peer.connection_role == ConnectionRole.INITIATING
            and peer.remote_address is not None
            and peer.remote_port is not None
        ):
            remote = Remote(address=peer.remote_address, port=peer.remote_port)
            return cls(peer=peer, framing=peer.framing, connection_role=ConnectionRole.INITIATING, remote=remote)
        else:
            if peer.bind_ip is None or peer.bind_port is None:
                raise ConnectionError("Invalid bind interface for accepting connection")
            bind = Bind(bind_address=peer.bind_ip, bind_port=peer.bind_port)
            return cls(peer=peer, framing=peer.framing, connection_role=ConnectionRole.ACCEPTING, bind=bind)

    def close(self):
        self.peer.stop_flag.set()
        self.connection.graceful_close()
        self.threads.graceful_close()
        self.peer._emit_connection_state(False)

    def _bind_tcp_acceptor(self):
        try:
            self.connection.binding = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.connection.binding.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.connection.binding.bind((self.bind.bind_address, self.bind.bind_port))
            self.connection.binding.listen(1)
            self.threads._acceptance_thread = threading.Thread(target=self._accept_tcp_connection, args=(), daemon=True)
            self.threads._acceptance_thread.start()
        except Exception as e:
            self.connection.graceful_close()
            raise PeerConnectionError(f"Error occurred while binding TCP acceptor: {e}")

    def _tcp_listener(self):
        try:
            if not self.peer.connected.is_set() or not self.connection.connection:
                raise PeerConnectionError("TCP listener cannot start until a client has connected")
            while self.peer.stop_flag.is_set() is False:
                read, _write, _exec = select([self.connection.connection], [], [], 0.01)
                for sock in read:
                    data = sock.recv(2**16)
                    if data == b"":
                        self.connection.graceful_close()
                        self.peer._emit_connection_state(False)
                        return
                    for msg in self.decoder.decode(data):
                        self.peer.dispatcher.dispatch(msg)
            self.connection.graceful_close()
        except Exception as e:
            listener_error = PeerListenerError(
                f"TCP listener failed for {self.peer.remote_address}:{self.peer.remote_port} - {e}"
            )
            self.peer._emit_error(listener_error)
            self.peer._emit_connection_state(False)

    def _initiate_tcp_connection(self):
        if self.remote:
            self.connection.connection = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.connection.connection.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
            self.connection.connection.connect((self.remote.address, self.remote.port))
            self.peer._emit_connection_state(True)
            self.threads._listener_thread = threading.Thread(target=self._tcp_listener, daemon=True)
            self.threads._listener_thread.start()
        else:
            raise PeerConnectionError("Remote peer must be provided for initiating connection")

    def _accept_tcp_connection(self):
        if not self.connection.binding:
            raise PeerConnectionError("TCP acceptor cannot accept connections without a binding socket")
        try:
            connection, address = self.connection.binding.accept()
            self.connection.connection = connection
            self.remote = Remote(address=address[0], port=address[1])
            self.peer._emit_connection_state(True)
            self.threads._listener_thread = threading.Thread(target=self._tcp_listener, daemon=True)
            self.threads._listener_thread.start()
        except Exception as e:
            self.connection.graceful_close()
            self.threads.graceful_close()
            self.peer._emit_connection_state(False)
            raise PeerConnectionError(f"Error occurred while accepting TCP connection: {e}")

    def send(self, packet):
        if not self.peer.connected.is_set() or not self.connection.connection:
            raise PeerConnectionError("Cannot send data, peer is not connected")
        try:
            encoded_packet = self.encoder.encode(packet)
            self.connection.connection.sendall(encoded_packet)
        except Exception as e:
            self.peer._emit_error(PeerConnectionError(f"Error occurred while sending TCP data: {e}"))

    def start(self):
        try:
            if self.connection_role == ConnectionRole.INITIATING:
                self._initiate_tcp_connection()

            else:
                self._bind_tcp_acceptor()
        except Exception as e:
            self.connection.graceful_close()
            self.threads.graceful_close()
            self.peer._emit_connection_state(False)
            raise PeerConnectionError(f"Error occurred while starting TCP transport: {e}")
