import inspect
import socket
import threading
from enum import Enum
from select import select
from typing import Any, Callable, Literal, overload

from oscparser import (
    OSCDecoder,
    OSCEncoder,
    OSCFraming,
    OSCMessage,
    OSCTransport,
)
from pydantic import BaseModel

from pyosc.call_handler import CallHandler, CallHandler_Response
from pyosc.dispatcher import Dispatcher, DispatcherInterface, Handler

from .acceptor import _accept_connection
from .connection import _tcp_listener
from .exceptions import PeerConfigurationError, PeerConnectionError, PeerListenerError
from .initiator import _initiate_connection
from .udp import _begin_udp


class remote(BaseModel):
    address: str
    port: int


class PeerRoles(Enum):
    INITIATING = "initiating"
    ACCEPTING = "accepting"


class Peer:
    """A Peer represents a remote OSC endpoint that can send and receive messages.

    Raises:
        Exception: If the connection to the peer cannot be established
    """

    @overload
    def __init__(
        self,
        *,
        connection_role: PeerRoles = PeerRoles.ACCEPTING,
        bind_address: str,
        bind_port: int,
        transport: Literal[OSCTransport.TCP],
        framing: OSCFraming = OSCFraming.OSC10,
        learning: bool = False,
    ): ...

    @overload
    def __init__(
        self,
        *,
        connection_role: PeerRoles = PeerRoles.INITIATING,
        remote_address: str,
        remote_port: int,
        transport: Literal[OSCTransport.TCP],
        framing: OSCFraming = OSCFraming.OSC10,
        learning: bool = False,
    ): ...

    @overload
    def __init__(
        self,
        *,
        remote_address: str,
        remote_port: int,
        bind_port: int,
        bind_address: str = "0.0.0.0",
        transport: Literal[OSCTransport.UDP],
        framing: OSCFraming = OSCFraming.OSC10,
        learning: bool = False,
    ): ...

    @overload
    def __init__(
        self,
        *,
        bind_port: int,
        bind_address: str = "",
        remote_port: int,
        transport: Literal[OSCTransport.UDP],
        framing: OSCFraming = OSCFraming.OSC10,
        learning: bool = True,
    ): ...

    def __init__(
        self,
        *,
        connection_role: PeerRoles | None = None,
        remote_address: str | None = None,
        remote_port: int | None = None,
        bind_address: str | None = "0.0.0.0",
        bind_port: int | None = None,
        transport: OSCTransport = OSCTransport.TCP,
        framing: OSCFraming = OSCFraming.OSC10,
        learning: bool = False,
    ):
        if connection_role is None and transport == OSCTransport.TCP:
            connection_role = PeerRoles.INITIATING
        self.remote_address = remote_address
        self.remote_port = remote_port
        self.address = remote_address
        self.port = remote_port
        self.bind_address = bind_address
        self.bind_port = bind_port
        self.stop_flag = threading.Event()
        self.transport = transport
        self.framing = framing
        self.connection_role = connection_role
        self.encoder = OSCEncoder(transport=self.transport, framing=self.framing)
        self.decoder = OSCDecoder(transport=self.transport, framing=self.framing)
        self.udp_bind_port = bind_port
        self.udp_bind_address = bind_address
        self.udp_rx_port = bind_port
        self.udp_rx_address = bind_address
        self.udp_remotes: list[remote] = []
        self.learning = learning
        if not self.remote_address:
            self.learning = True
        # Initialize connection attributes so static checkers know they exist
        self.bind: socket.socket | None = None
        self.tcp_connection: socket.socket | None = None
        self.udp_connection: socket.socket | None = None
        self.accept_background: threading.Thread | None = None
        self.listener_background: threading.Thread | None = None
        self.connected = threading.Event()
        self.last_error: Exception | str | None = None
        self.background: threading.Thread | None = None
        self._event_handlers: dict[str, list[Callable[..., None]]] = {
            "connect": [],
            "disconnect": [],
            "error": [],
        }
        if self.connection_role and self.transport == OSCTransport.TCP:
            # Connection roles only apply to TCP peers, as UDP is connectionless. If a connection role is specified for a UDP peer, raise an error.
            if self.connection_role == PeerRoles.INITIATING:
                self.tcp_connection = _initiate_connection(self)
                self.dispatcher = Dispatcher(error_emit=self._emit_error)
                self.callHandler = CallHandler(self)

            else:
                _accept_connection(self)
                self.dispatcher = Dispatcher(error_emit=self._emit_error)
                self.callHandler = CallHandler(self)

        elif not self.connection_role and self.transport == OSCTransport.UDP:
            if self.remote_address and self.remote_port:
                self.udp_remotes.append(remote(address=self.remote_address, port=self.remote_port))
            self.udp_connection = _begin_udp(self)
            self.dispatcher = Dispatcher(error_emit=self._emit_error)
            self.callHandler = CallHandler(self)

    @property
    def connection(self) -> socket.socket | None:
        """Returns the active transport socket for this peer."""
        if self.transport == OSCTransport.TCP:
            if self.tcp_connection:
                return self.tcp_connection
            else:
                raise PeerConnectionError("TCP connection is not established.")
        elif self.transport == OSCTransport.UDP:
            if self.udp_connection:
                return self.udp_connection
            else:
                raise PeerConnectionError("UDP connection is not established.")

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

    def _emit_error(self, error: Exception | str):
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
            if self.transport == OSCTransport.TCP:
                tcp_connection = self.tcp_connection
                if tcp_connection is None:
                    raise PeerConnectionError("TCP connection is not established.")
                tcp_connection.sendall(encoded_message)
            elif self.transport == OSCTransport.UDP:
                udp_connection = self.udp_connection
                if udp_connection is None:
                    raise PeerConnectionError("UDP connection is not established.")
                if self.udp_remotes.__len__() == 0:
                    if self.learning:
                        raise PeerConnectionError(
                            "No remote addresses are known for this UDP peer. Specify a remote address if you want to send messages before receiving messages."
                        )
                for remote in self.udp_remotes:
                    udp_connection.sendto(encoded_message, (remote.address, remote.port))
        except OSError as e:
            peer_error = PeerConnectionError(f"Failed to send OSC message to {self.remote_address}:{self.remote_port} - {e}")
            self._emit_error(peer_error)
            raise peer_error from e

        """Proxy Methods: Proxy methods exist for the purpose of an nicer developer experience.
        """

    def handler(self, *args, **kwargs):
        """Proxy method for the dispatcher's handler decorator."""
        return self.dispatcher.handler(*args, **kwargs)

    @overload
    def register_handler(self, message_address: str, func: DispatcherInterface[OSCMessage]) -> Handler: ...

    @overload
    def register_handler[T: BaseModel](
        self, message_address: str, func: DispatcherInterface[OSCMessage], validator: type[T]
    ) -> Handler: ...

    def register_handler[T: BaseModel](
        self,
        message_address: str,
        func: DispatcherInterface[OSCMessage],
        validator: type[T] = OSCMessage,
    ) -> Handler:
        return self.dispatcher.register_handler(message_address, func, validator)

    """
    Call methods require overloads to properly type hint the various return types based on the presence of a validator. The implementation is all handled by the CallHandler class, which the Peer class proxies to for a nicer developer experience."""

    @overload
    def call(
        self,
        message: OSCMessage,
        *,
        message_return_address: str | None = None,
        timeout: float = 5.0,
        max_responses: int = 1,
        prefix: int = 0,
    ) -> CallHandler_Response[OSCMessage] | list[CallHandler_Response[OSCMessage]] | None: ...

    @overload
    def call[T: BaseModel](
        self,
        message: OSCMessage,
        *,
        message_return_address: str | None = None,
        validator: type[T],
        timeout: float = 5.0,
        max_responses: int = 1,
        prefix: int = 0,
    ) -> CallHandler_Response[T] | list[CallHandler_Response[T]] | None: ...

    def call(
        self,
        message: OSCMessage,
        *,
        message_return_address: str | None = None,
        validator: type[BaseModel] = OSCMessage,
        timeout: float = 5.0,
        max_responses: int = 1,
        prefix: int = 0,
    ) -> CallHandler_Response[Any] | list[CallHandler_Response[Any]] | None:
        """

        Args:
            message (OSCMessage): The OSCMessage to send as the call request.
            message_return_address (str | None, optional): The address to which the response should be sent. Defaults to None.
            validator (type[BaseModel], optional): The validator to use for the response. Defaults to OSCMessage.
            timeout (float, optional): The timeout for the call. Defaults to 5.0.
            max_responses (int, optional): The maximum number of responses to wait for. Defaults to 1.
            prefix (int, optional): The number of leading arguments in the response to ignore when validating. Defaults to 0.

        Returns:
            CallHandler_Response | None: A CallHandler_Response containing the response message and latency, or None if the call timed out.
        """
        return self.callHandler.call(
            message,
            return_address=message_return_address,
            validator=validator,
            timeout=timeout,
            max_responses=max_responses,
            prefix=prefix,
        )

    def listen_tcp(self):
        """Initiates a background TCP listener

        Raises:
            e: Any exceptions raised during listening are propagated upwards
        """
        if self.connection_role == PeerRoles.ACCEPTING:
            _accept_connection(self)
            return

        self.listener_background = threading.Thread(target=_tcp_listener, daemon=True)
        self.listener_background.start()

    def listen_udp(self):
        """Initiates a background UDP listener against the peer

        Raises:
            e: Any exceptions raised during listening are propagated upwards
        """
        try:
            learning = self.learning
            udp_connection = self.udp_connection
            if udp_connection is None:
                raise PeerConnectionError("UDP connection is not established.")

            while self.stop_flag.is_set() is False:
                read, _write, _exec = select([udp_connection], [], [], 0.01)
                for sock in read:
                    data, addr = sock.recvfrom(2**16)
                    if addr[0] != self.remote_address:
                        if not learning:
                            continue
                        else:
                            if addr[0] not in [remote.address for remote in self.udp_remotes]:
                                if not self.remote_port:
                                    raise PeerConfigurationError(
                                        "UDP remote port must be specified for UDP Peers in learning mode"
                                    )
                                self.udp_remotes.append(remote(address=addr[0], port=self.remote_port))
                    for msg in self.decoder.decode(data):
                        self.dispatcher.dispatch(msg)
            udp_connection.close()
            self._emit_connection_state(False)
        except Exception as e:
            listener_error = PeerListenerError(f"UDP listener failed for {self.remote_address}:{self.remote_port} - {e}")
            self._emit_error(listener_error)
            self._emit_connection_state(False)

    def start_listening(self):
        """Invokes above methods to start a connection dependant on mode."""
        # Start the dispatcher's scheduler for timestamped bundles
        self.dispatcher.start_scheduler()
        if self.transport == OSCTransport.TCP:
            if self.connection_role == PeerRoles.INITIATING:
                self.listener_background = threading.Thread(target=_tcp_listener, daemon=True)
                self.listener_background.start()
        elif self.transport == OSCTransport.UDP:
            self.background = threading.Thread(target=self.listen_udp, daemon=True)
            self.background.start()

    def stop_listening(self):
        """Stops listening to incoming messages byterminating the background thread"""
        self.stop_flag.set()
        if self.accept_background is not None and self.accept_background.is_alive():
            self.accept_background.join(timeout=1)
        if self.listener_background is not None and self.listener_background.is_alive():
            self.listener_background.join(timeout=1)
        if self.background is not None and self.background.is_alive():
            self.background.join(timeout=1)
        if self.bind is not None:
            self.bind.close()
        if self.tcp_connection is not None:
            self.tcp_connection.close()
        if self.udp_connection is not None:
            self.udp_connection.close()
        self._emit_connection_state(False)
        # Stop the scheduler as well
        self.dispatcher.stop_scheduler()
