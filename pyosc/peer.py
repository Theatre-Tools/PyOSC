import inspect
import socket
import threading
from select import select
from typing import Callable, Literal, overload

from oscparser import (
    OSCDecoder,
    OSCEncoder,
    OSCFraming,
    OSCMessage,
    OSCModes,
)

from pyosc.dispatcher import Dispatcher


class PeerError(Exception):
    """Base exception for peer-related errors."""


class PeerConfigurationError(PeerError):
    """Raised when a peer is configured with invalid arguments."""


class PeerConnectionError(PeerError):
    """Raised when a peer cannot establish or use its transport connection."""


class PeerListenerError(PeerError):
    """Raised when a background listener fails."""


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
        self.connected = threading.Event()
        self.last_error: Exception | None = None
        self.background: threading.Thread | None = None
        self._event_handlers: dict[str, list[Callable[..., None]]] = {
            "connect": [],
            "disconnect": [],
            "error": [],
        }
        if self.mode == OSCModes.TCP:
            try:
                self.tcp_connection = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                self.tcp_connection.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
                self.tcp_connection.connect((self.address, self.port))
            except OSError as e:
                raise PeerConnectionError(f"Could not connect to TCP Peer at {self.address}:{self.port} - {e}") from e
            self._emit_connection_state(True)
        elif self.mode == OSCModes.UDP:
            try:
                if self.udp_rx_address is None:
                    raise PeerConfigurationError("UDP RX address must be specified for UDP Peers")
                if self.udp_rx_port is None:
                    raise PeerConfigurationError("UDP RX port must be specified for UDP Peers")
                self.udp_connection = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                self.udp_connection.bind((self.udp_rx_address, self.udp_rx_port))
            except OSError as e:
                raise PeerConnectionError(f"Could not bind UDP Peer at localhost:{self.udp_rx_port} - {e}") from e
            self._emit_connection_state(True)
        self.Dispatcher = Dispatcher()

    @property
    def connection(self) -> socket.socket:
        """Returns the active transport socket for this peer."""
        if self.mode == OSCModes.TCP:
            return self.tcp_connection
        return self.udp_connection

    def _normalize_event_name(self, raw_name: str) -> str:
        aliases = {
            "connect": "connect",
            "connection": "connect",
            "disconnect": "disconnect",
            "disconnection": "disconnect",
            "error": "error",
            "exception": "error",
        }
        normalized = aliases.get(raw_name)
        if normalized is None:
            raise ValueError(f"Unsupported event type: {raw_name}")
        return normalized

    def event(self, func: Callable[..., None]):
        """Decorator event registration inferred from function name.

        Supported handler names:
        - ``on_connect`` / ``on_connection``
        - ``on_disconnect`` / ``on_disconnection``
        - ``on_error`` / ``on_exception``
        """
        name = func.__name__
        params = len(inspect.signature(func).parameters)
        if not name.startswith("on_"):
            raise ValueError("Event handler name must start with 'on_'")

        event_name = self._normalize_event_name(name[3:])
        if name[3:] not in {
            "connect",
            "connection",
            "disconnect",
            "disconnection",
            "error",
            "exception",
        }:
            raise ValueError(f"Unsupported event type in handler name: {name}")

        if event_name in {"connect", "disconnect"}:
            if params == 0:

                def callback(_peer):
                    func()
            else:
                callback = func

            self._event_handlers[event_name].append(callback)
            if event_name == "connect" and self.connected.is_set():
                callback(self)
        elif event_name == "error":
            if params == 1:
                self._event_handlers[event_name].append(lambda _peer, error: func(error))
            else:
                self._event_handlers[event_name].append(func)
        return func

    def _emit(self, event_name: str, *args):
        handlers = self._event_handlers.get(event_name, [])
        for handler in handlers:
            handler(*args)

    def _emit_error(self, error: Exception):
        self.last_error = error
        self._emit("error", self, error)

    def _emit_connection_state(self, is_connected: bool):
        if is_connected:
            self.connected.set()
            self._emit("connect", self)
        else:
            self.connected.clear()
            self._emit("disconnect", self)

    def send_message(self, message: OSCMessage):
        """
        Sends an OSC packet with a given message to the peer
        - ``message``: The OSCMessage to send
        Raises:
            e: Any exceptions raised during sending are propagated upwards

        """
        try:
            encoded_message = self.encoder.encode(message)
            if self.mode == OSCModes.TCP:
                self.tcp_connection.sendall(encoded_message)
            elif self.mode == OSCModes.UDP:
                self.udp_connection.sendto(encoded_message, (self.address, self.port))
        except OSError as e:
            peer_error = PeerConnectionError(f"Failed to send OSC message to {self.address}:{self.port} - {e}")
            self._emit_error(peer_error)
            raise peer_error from e

    def listen_tcp(self):
        """Initiates a background TCP listener against the peer

        Raises:
            e: Any exceptions raised during listening are propagated upwards
        """
        try:
            while self.stop_flag.is_set() is False:
                read, _write, _exec = select([self.tcp_connection], [], [], 0.01)
                for sock in read:
                    data = sock.recv(2**16)
                    if data == b"":
                        self.tcp_connection.close()
                        self._emit_connection_state(False)
                        return
                    for msg in self.decoder.decode(data):
                        self.Dispatcher.dispatch(msg)
            self.tcp_connection.close()
        except Exception as e:
            listener_error = PeerListenerError(f"TCP listener failed for {self.address}:{self.port} - {e}")
            self._emit_error(listener_error)
            self._emit_connection_state(False)

    def listen_udp(self):
        """Initiates a background UDP listener against the peer

        Raises:
            e: Any exceptions raised during listening are propagated upwards
        """
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
            self._emit_connection_state(False)
        except Exception as e:
            listener_error = PeerListenerError(f"UDP listener failed for {self.address}:{self.port} - {e}")
            self._emit_error(listener_error)
            self._emit_connection_state(False)

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
        if self.background is not None and self.background.is_alive():
            self.background.join(timeout=1)
        self._emit_connection_state(False)
        # Stop the scheduler as well
        self.Dispatcher.stop_scheduler()
