import inspect
import threading
from typing import Callable, Literal, overload

from oscparser import (
    OSCFraming,
    OSCMessage,
    OSCTransport,
)
from pydantic import BaseModel

from pyosc.call_handler import CallHandler
from pyosc.dispatcher import Dispatcher, DispatcherInterface, Handler

from .transport import ConnectionRole, Remote, Transport


class Peer:
    """A Peer represents a remote OSC endpoint that can send and receive messages.

    Raises:
        Exception: If the connection to the peer cannot be established
    """

    send_message: Callable[[OSCMessage], None]

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
        if self.remote_address and self.remote_port:
            self.remotes.append(Remote(address=self.remote_address, port=self.remote_port))
        if not self.remote_address:
            self.learning = True
        self.connected = threading.Event()
        self.last_error: Exception | str | None = None
        self.background: threading.Thread | None = None
        self._event_handlers: dict[str, list[Callable[..., None]]] = {
            "connect": [],
            "disconnect": [],
            "error": [],
        }
        self.connection = Transport.from_peer(self)
        self.dispatcher = Dispatcher(error_emit=self._emit_error)
        self.callHandler = CallHandler(self)
        self.send_message = self.connection.send

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

    def start_listening(self):
        """Invokes above methods to start a connection dependant on mode."""
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
        if self.connection:
            self.connection.close()
            self._emit_connection_state(False)
            self.dispatcher.stop_scheduler()
        else:
            raise RuntimeError("No connection to stop listening on.")
