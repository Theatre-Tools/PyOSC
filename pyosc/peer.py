import inspect
import socket
import threading
from typing import Any, Callable, Literal, overload

from oscparser import (
    OSCFraming,
    OSCMessage,
    OSCTransport,
)
from pydantic import BaseModel

from pyosc.call_handler import CallHandler, CallHandler_Response
from pyosc.dispatcher import Dispatcher, DispatcherInterface, Handler

from .tcp import TCPTransport
from .transport import ConnectionRole, Remote, Transport
from .udp import UDPTransport


class Peer:
    """A Peer represents a remote OSC endpoint that can send and receive messages.

    Raises:
        Exception: If the connection to the peer cannot be established
    """

    @overload
    def __init__(
        self,
        *,
        connection_role: ConnectionRole = ConnectionRole.ACCEPTING,
        bind_ip: str,
        bind_port: int,
        transport: Literal[OSCTransport.TCP],
        framing: OSCFraming = OSCFraming.OSC10,
        learning: bool = False,
    ): ...

    @overload
    def __init__(
        self,
        *,
        connection_role: ConnectionRole = ConnectionRole.INITIATING,
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
        bind_ip: str = "0.0.0.0",
        transport: Literal[OSCTransport.UDP],
        framing: OSCFraming = OSCFraming.OSC10,
        learning: bool = False,
    ): ...

    @overload
    def __init__(
        self,
        *,
        bind_port: int,
        bind_ip: str = "",
        remote_port: int,
        transport: Literal[OSCTransport.UDP],
        framing: OSCFraming = OSCFraming.OSC10,
        learning: bool = True,
    ): ...

    def __init__(
        self,
        *,
        connection_role: ConnectionRole | None = None,
        remote_address: str | None = None,
        remote_port: int | None = None,
        bind_ip: str | None = "0.0.0.0",
        bind_port: int | None = None,
        transport: OSCTransport = OSCTransport.TCP,
        framing: OSCFraming = OSCFraming.OSC10,
        learning: bool = False,
    ):
        if connection_role is None and transport == OSCTransport.TCP:
            connection_role = ConnectionRole.INITIATING
        self.connection: Transport | None = None
        self.remote_address = remote_address
        self.remote_port = remote_port
        self.bind_ip = bind_ip
        self.bind_port = bind_port
        self.stop_flag = threading.Event()
        self.transport = transport
        self.framing = framing
        self.connection_role = connection_role
        self.learning = learning
        self.remotes: list[Remote] = []
        if not self.remote_address:
            self.learning = True
        # Initialize connection attributes so static checkers know they exist
        self.bind: socket.socket | None = None
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
        if transport == OSCTransport.UDP:
            self.connection = UDPTransport.from_peer(self)
        else:
            self.connection = TCPTransport.from_peer(self)
        self.dispatcher = Dispatcher(error_emit=self._emit_error)
        self.callHandler = CallHandler(self)

        ##if self.connection_role and self.transport == OSCTransport.TCP:
        ##    # Connection roles only apply to TCP peers, as UDP is connectionless. If a connection role is specified for a UDP peer, raise an error.
        ##    if self.connection_role == ConnectionRole.INITIATING:
        ##        self.tcp_connection = _initiate_connection(self)
        ##        self.dispatcher = Dispatcher(error_emit=self._emit_error)
        ##        self.callHandler = CallHandler(self)
        ##    else:
        ##        _accept_connection(self)
        ##        self.dispatcher = Dispatcher(error_emit=self._emit_error)
        ##        self.callHandler = CallHandler(self)

    ##
    ##elif not self.connection_role and self.transport == OSCTransport.UDP:
    ##    if self.remote_address and self.remote_port:
    ##        self.remotes.append(Remote(address=self.remote_address, port=self.remote_port))
    ##

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
        try:
            handlers = self._event_handlers.get(event_name, [])
            for handler in handlers:
                handler(*args)
        except Exception as e:
            self._emit_error(e)
            if self.connection:
                self.connection.close()

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
        raise NotImplementedError("send_message is not implemented in the base Peer class. Use a specific transport class.")

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
    Call methods require overloads to properly type hint the various return types based on the presence of a validator.
    The implementation is all handled by the CallHandler class, which the Peer class proxies to for a nicer developer experience."""

    @overload
    def call(
        self,
        message: OSCMessage,
        *,
        message_return_address: str | None = None,
        timeout: float = 5.0,
        max_responses: int = 1,
        prefix: int = 0,
    ) -> CallHandler_Response[OSCMessage] | None: ...

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
    ) -> CallHandler_Response[T] | None: ...

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
        Proxies the call to the CallHandler instance for this peer.

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
            message_return_address=message_return_address,
            validator=validator,
            timeout=timeout,
            max_responses=max_responses,
            prefix=prefix,
        )

    def start_listening(self):
        """Invokes above methods to start a connection dependant on mode."""
        # Start the dispatcher's scheduler for timestamped bundles
        self.dispatcher.start_scheduler()
        try:
            if self.connection:
                self.connection.start()
        except Exception as e:
            self._emit_error(e)
        except KeyboardInterrupt:
            print("KeyboardInterrupt received. Stopping listening.")
            if self.connection:
                self.connection.close()

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
        self._emit_connection_state(False)
        # Stop the scheduler as well
        self.dispatcher.stop_scheduler()
