import socket
import threading
from select import select
from typing import TYPE_CHECKING

from oscparser import OSCBundle, OSCDecoder, OSCEncoder, OSCFraming, OSCMessage, OSCTransport

from .exceptions import PeerConfigurationError, PeerConnectionError, PeerListenerError
from .transport import Remote, Transport

if TYPE_CHECKING:
    from .peer import Peer


class UDPTransport(Transport):
    def __init__(
        self, bind_ip, bind_port, remotes, remote_port, peer, framing: OSCFraming = OSCFraming.OSC10, learning: bool = False
    ):
        self.peer = peer
        self.bind_ip = bind_ip
        self.bind_port = bind_port
        self.remotes: list[Remote] = remotes
        self.remote_port = remote_port
        self.encoder = OSCEncoder(transport=OSCTransport.UDP, framing=framing)
        self.decoder = OSCDecoder(transport=OSCTransport.UDP, framing=framing)
        self.learning = learning

    @classmethod
    def create_from_peer(cls, peer: Peer) -> "UDPTransport":
        return cls(
            bind_ip=peer.bind_ip,
            bind_port=peer.bind_port,
            remotes=peer.remotes,
            remote_port=peer.remote_port,
            peer=peer,
            framing=peer.framing,
            learning=peer.learning,
        )

    def _listener_thread(self):
        try:
            while self.peer.stop_flag.is_set() is False:
                read, _write, _exec = select([self.conn], [], [], 0.01)
                for sock in read:
                    data, addr = sock.recvfrom(2**16)
                    if addr[0] not in [remote.address for remote in self.remotes]:
                        if not self.learning:
                            pass
                        else:
                            if addr[0] not in [remote.address for remote in self.remotes]:
                                if not self.remote_port:
                                    raise PeerConfigurationError(
                                        "UDP remote port must be specified for UDP Peers in learning mode"
                                    )
                                self.remotes.append(Remote(address=addr[0], port=self.remote_port))
                    for msg in self.decoder.decode(data):
                        self.peer.dispatcher.dispatch(msg)
            self.conn.close()
            self.peer._emit_connection_state(False)
        except Exception as e:
            listener_error = PeerListenerError(f"UDP listener failed for {self.bind_ip}:{self.bind_port} - {e}")
            self.peer._emit_error(listener_error)
            self.peer._emit_connection_state(False)
        finally:
            self.peer._emit_connection_state(False)
            if hasattr(self, "conn"):
                self.conn.close()

    def start(self):
        try:
            conn = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            conn.bind((self.bind_ip, self.bind_port))
            self.peer._emit_connection_state(True)
            self.conn = conn
            self.background = threading.Thread(target=self._listener_thread, daemon=True)
            self.background.start()

        except OSError as e:
            raise PeerConfigurationError(f"Could not bind UDP Peer to {self.bind_ip}:{self.bind_port} - {e}") from e

    def send(self, packet: OSCMessage | OSCBundle):
        if self.conn is None:
            raise PeerConnectionError("UDP connection is not established.")
        encoded_packet = self.encoder.encode(packet)
        if self.peer.remotes.__len__() == 0:
            if self.learning:
                raise PeerConnectionError(
                    "No remote addresses are known for this UDP peer. Specify a remote address if you want to send messages before receiving messages."
                )
        for remote in self.peer.remotes:
            try:
                self.conn.sendto(encoded_packet, (remote.address, remote.port))
            except OSError as e:
                raise PeerConnectionError(f"Could not send UDP packet to {remote.address}:{remote.port} - {e}") from e

    def close(self):
        self.peer.stop_flag.set()
        if hasattr(self, "conn"):
            self.conn.close()
        self.peer._emit_connection_state(False)
