import socket
import threading
from select import select
from typing import Literal, overload

from oscparser import (
    OSCDecoder,
    OSCEncoder,
    OSCFraming,
    OSCMessage,
    OSCModes,
)

from pyosc.dispatcher import Dispatcher


class Peer:
    """A Peer represents a remote OSC endpoint that can send and receive messages.

    Raises:
        Exception: If the connection to the peer cannot be established
    """

    @overload
    def __init__(
        self,
        address: str,
        port: int,
        *,
        mode: Literal[OSCModes.TCP],
        framing: OSCFraming = OSCFraming.OSC10,
    ): ...

    @overload
    def __init__(
        self,
        address: str,
        port: int,
        *,
        udp_rx_port: int,
        udp_rx_address: str,
        mode: Literal[OSCModes.UDP],
        framing: OSCFraming = OSCFraming.OSC10,
    ): ...

    def __init__(
        self,
        address: str,
        port: int,
        *,
        mode: OSCModes = OSCModes.TCP,
        udp_rx_port: int | None = None,
        udp_rx_address: str | None = None,
        framing: OSCFraming = OSCFraming.OSC10,
    ):
        self.address = address
        self.port = port
        self.stop_flag = threading.Event()
        self.mode = mode
        self.framing = framing
        self.encoder = OSCEncoder(mode=self.mode, framing=self.framing)
        self.decoder = OSCDecoder(mode=self.mode, framing=self.framing)
        self.udp_rx_port = udp_rx_port
        self.udp_rx_address = udp_rx_address
        if self.mode == OSCModes.TCP:
            try:
                self.tcp_connection = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                self.tcp_connection.connect((self.address, self.port))
            except OSError as e:
                raise Exception(f"Could not connect to TCP Peer at {self.address}:{self.port} - {e}")
        elif self.mode == OSCModes.UDP:
            try:
                if self.udp_rx_address is None:
                    raise Exception("UDP RX address must be specified for UDP Peers")
                self.udp_connection = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                self.udp_connection.bind((self.udp_rx_address, self.udp_rx_port))
            except OSError as e:
                raise Exception(f"Could not bind UDP Peer at localhost:{self.udp_rx_port} - {e}")
        self.Dispatcher = Dispatcher()

    def send_message(self, message: OSCMessage):
        """
        Sends an OSC packet with a given message to the peer
        - ``message``: The OSCMessage to send
        Raises:
            e: Any exceptions raised during sending are propagated upwards

        """
        if self.mode == OSCModes.TCP:
            encoded_message = self.encoder.encode(message)
            self.tcp_connection.sendall(encoded_message)
        elif self.mode == OSCModes.UDP:
            encoded_message = self.encoder.encode(message)
            self.udp_connection.sendto(encoded_message, (self.address, self.port))

    def listen_tcp(self):
        """Initiates a background TCP listener against the peer

        Raises:
            e: Any exceptions raised during listening are propagated upwards
        """
        print("Listening on TCP \n")
        try:
            while self.stop_flag.is_set() is False:
                read, _write, _exec = select([self.tcp_connection], [], [], 0.01)
                for sock in read:
                    data = sock.recv(2**16)
                    if data == b"":
                        self.tcp_connection.close()
                        return
                    for msg in self.decoder.decode(data):
                        self.Dispatcher.dispatch(msg)
            self.tcp_connection.close()
            print("socket closed")
        except Exception as e:
            raise e

    def listen_udp(self):
        """Initiates a background UDP listener against the peer

        Raises:
            e: Any exceptions raised during listening are propagated upwards
        """
        print("Listening on UDP \n")
        try:
            while self.stop_flag.is_set() is False:
                read, _write, _exec = select([self.udp_connection], [], [], 0.01)
                for sock in read:
                    data, addr = sock.recvfrom(2**16)
                    if addr[0] != self.address:
                        continue
                    for msg in self.decoder.decode(data):
                        self.Dispatcher.dispatch(msg)
            self.udp_connection.close()
        except Exception as e:
            raise e

    def start_listening(self):
        """Invokes above methods to start a connection dependant on mode."""
        # Start the dispatcher's scheduler for timestamped bundles
        self.Dispatcher.start_scheduler()

        if self.mode == OSCModes.TCP:
            self.background = threading.Thread(target=self.listen_tcp, daemon=True)
            self.background.start()
        elif self.mode == OSCModes.UDP:
            self.background = threading.Thread(target=self.listen_udp, daemon=True)
            self.background.start()

    def stop_listening(self):
        """Stops listening to incoming messages by terminating the background thread"""
        self.stop_flag.set()
        if self.background.is_alive():
            self.background.join(timeout=1)
        # Stop the scheduler as well
        self.Dispatcher.stop_scheduler()
