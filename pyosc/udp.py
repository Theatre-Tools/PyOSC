import socket

from oscparser import OSCBundle, OSCDecoder, OSCEncoder, OSCFraming, OSCMessage, OSCTransport

from .exceptions import PeerConfigurationError, PeerConnectionError
from .transport import Transport


class UDPTransport(Transport):
    def __init__(self, bind_ip, bind_port, remotes, remote_port, peer, framing: OSCFraming = OSCFraming.OSC10, learning: bool = False):
        self.peer = peer
        self.bind_ip = bind_ip
        self.bind_port = bind_port
        self.remotes: list = remotes
        self.remote_port = remote_port
        self.encoder = OSCEncoder(transport=OSCTransport.UDP, framing=framing)
        self.decoder = OSCDecoder(transport=OSCTransport.UDP, framing=framing)
        self.learning = learning

    @classmethod
    def from_peer(cls, peer):
        return cls(
            bind_ip=peer.bind_ip,
            bind_port=peer.bind_port,
            remotes=peer.remotes,
            remote_port=peer.remote_port,
            peer=peer,
            framing=peer.framing,
            learning=peer.learning
        )

    def _begin_udp(self) -> socket.socket | None:
        try:
            conn = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            conn.bind((self.bind_ip, self.bind_port))
            self.peer._emit_connection_state(True)
            self.conn = conn
        except OSError as e:
            raise PeerConfigurationError(
                f"Could not bind UDP Peer to {self.bind_ip}:{self.bind_port} - {e}") from e
        finally:
            self.peer._emit_connection_state(False)
            if hasattr(self, 'conn'):
                self.conn.close()

    def start(self):
        self.udp_connection = self._begin_udp()

    def send(self, packet: OSCMessage | OSCBundle):
        if self.conn is None:
            raise PeerConnectionError("UDP connection is not established.")
        encoded_packet = self.encoder.encode(packet)
        if self.remotes.__len__() == 0:
            if self.learning:
                raise PeerConnectionError(
                    "No remote addresses are known for this UDP peer. Specify a remote address if you want to send messages before receiving messages."
                )
        for remote in self.remotes:
            try:
                self.conn.sendto(
                    encoded_packet, (remote.address, remote.port))
            except OSError as e:
                raise PeerConnectionError(
                    f"Could not send UDP packet to {remote.address}:{remote.port} - {e}") from e
            finally:
                self.peer._emit_connection_state(False)
                if hasattr(self, 'conn'):
                    self.conn.close()
