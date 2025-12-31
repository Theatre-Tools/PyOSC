import socket
import threading
from typing import Callable

from oscparser import (
    OSCArg,
    OSCBundle,
    OSCDecoder,
    OSCEncoder,
    OSCFraming,
    OSCMessage,
    OSCModes,
)
from oscparser.types import OSCArray, OSCFalse, OSCFloat, OSCInt, OSCString, OSCTrue


class Framing:
    OSC10 = OSCFraming.OSC10
    OSC11 = OSCFraming.OSC11


class Modes:
    TCP = OSCModes.TCP
    UDP = OSCModes.UDP


class Message:
    """Abstractified the OSCMessage for easier use within the Peer class
     - ``address``: The OSC Address of the message
    - ``args``: A tuple of OSCArgs contained within the message

        This class will then convert them to OSCArgs internally
    """

    def __init__(self, address: str, args: list = []):
        self.address = address
        self.args = args

    def to_message(self) -> OSCMessage:
        """Used by the module to get a OSCMessage object to send to the peer

        Returns:
            OSCMessage: Returns an OSC message
        """
        self.newargs = []
        for arg in self.args:
            ## If it is a native python type, convert it to an OSCArg
            if not isinstance(arg, OSCArg):
                if not isinstance(arg, list):
                    self.newargs.append(  # type: ignore
                        self.to_arg(arg),
                    )
                else:
                    self.newargs.append(self._convert_array_recursive(arg))
            else:
                self.newargs += (arg,)

        return OSCMessage(
            address=self.address,
            args=tuple(
                self.newargs,
            ),
        )

    def _convert_array_recursive(self, array: list) -> OSCArray:
        """Recursively converts a list (potentially with nested lists) to an OSCArray

        Args:
            array: The list to convert, may contain nested lists

        Returns:
            OSCArray: An OSCArray with items recursively converted
        """
        converted_items = []
        for item in array:
            if isinstance(item, OSCArg):
                converted_items.append(item)
            elif isinstance(item, list):
                converted_items.append(self._convert_array_recursive(item))
            else:
                converted_items.append(self.to_arg(item))
        return OSCArray(items=tuple(converted_items))

    @staticmethod
    def _from_array_recursive(osc_array: OSCArray) -> list:
        """Recursively converts an OSCArray (potentially with nested arrays) to a native Python list

        Args:
            osc_array: The OSCArray to convert, may contain nested OSCArrays

        Returns:
            list: A native Python list with items recursively converted
        """
        result = []
        for item in osc_array.items:
            if isinstance(item, OSCArray):
                result.append(Message._from_array_recursive(item))
            else:
                result.append(Message.from_arg(item))
        return result

    @staticmethod
    def to_arg(arg):
        try:
            if isinstance(arg, OSCArray):
                return Message._from_array_recursive(arg)
            if isinstance(arg, int):
                return OSCInt(value=arg)
            elif isinstance(arg, str):
                return OSCString(value=arg)
            elif isinstance(arg, bool):
                if arg:
                    return OSCTrue()
                else:
                    return OSCFalse()
            elif isinstance(arg, float):
                return OSCFloat(value=arg)
        except Exception as e:
            raise e

    @staticmethod
    def from_arg(arg: OSCArg):
        """Converts an OSCArg to a native python type"""
        if isinstance(arg, OSCInt):
            return arg.value
        elif isinstance(arg, OSCString):
            return arg.value
        elif isinstance(arg, OSCFloat):
            return arg.value
        elif isinstance(arg, OSCTrue):
            return True
        elif isinstance(arg, OSCFalse):
            return False
        elif isinstance(arg, OSCArray):
            array = []
            for item in arg.items:
                # Recursively handle nested arrays
                array.append(Message.from_arg(item))
            return array

    @staticmethod
    def from_message(message: OSCMessage):
        """Converts an OSCMessage to a Message object, does the inverse of to_message"""

        ## take in the args, and convert them from OSCArgs to native python types
        args = []
        for arg in message.args:
            args.append(Message.from_arg(arg))
        return Message(address=message.address, args=args)


class Dispatcher:
    """Dispatches incoming OSC messages to registered handlers based on their addresses."""

    def __init__(self):
        self.handlers = {}

    Handler = Callable[[OSCMessage], None]

    def add_handler(self, address: str, handler: Handler):
        """
        Add a handler for a specific OSC address.
        - ``address``: The OSC address to handle.
        - ``handler``: A callable that takes an OSCMessage as its only argument.
        """
        if address in self.handlers:
            raise ValueError(f"Handler already exists for address {address}")
        if address.endswith("/") and len(address) > 1:
            address = address[:-1]
        self.handlers[address] = handler

    def remove_handler(self, address: str):
        """
        Removes a handler for a specific OSC address.
        - ``address``: The OSC address to remove the handler for.
        """
        if address in self.handlers:
            del self.handlers[address]
        else:
            raise ValueError(f"No handler exists for address {address}")

    def add_default_handler(self, handler: Handler):
        """
        Adds a fallback default handler to any messages that don't have a specific handler assigned.
        - ``handler``: A callable that takes an OSCMessage as its only argument.
        """
        self.handlers[""] = handler

    def dispatch(self, message: OSCMessage):
        """
        Dispatches an incoming OSC message to the appropriate handler based on its address.
        - ``message``: The incoming OSCMessage to dispatch.
        """
        ## Split the address into it's parts
        ## This allows us to iterate over every part of it in order to match wildcards and less specific addresses
        parts = message.address.split("/")
        for i in range(len(parts), 0, -1):
            addr_to_check = "/".join(parts[:i])
            if addr_to_check in self.handlers:
                self.handlers[addr_to_check](Message.from_message(message))
                return


class Peer:
    """An OSC Peer that can send and receive OSC messages over TCP or UDP."""

    def __init__(
        self,
        address: str,
        port: int,
        dispatcher: Dispatcher,
        mode: OSCModes = OSCModes.UDP,
        framing=OSCFraming.OSC10,
        udp_rx_port: int = 8001,
    ):
        self.address = address
        self.port = port
        self.message = OSCMessage
        self.args = OSCArg
        self.mode = mode
        self.framing = framing
        self.encoder = OSCEncoder(mode=self.mode, framing=self.framing)
        self.decoder = OSCDecoder(mode=self.mode, framing=self.framing)
        self.udpRxPort = udp_rx_port
        if self.mode == OSCModes.TCP:
            try:
                self.tcp_connection = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                self.tcp_connection.connect((self.address, self.port))
            except OSError as e:
                raise Exception(f"Could not connect to TCP Peer at {self.address}:{self.port} - {e}")
        elif self.mode == OSCModes.UDP:
            try:
                self.udp_connection = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                self.udp_connection.bind(("localhost", self.udpRxPort))
            except OSError as e:
                raise Exception(f"Could not bind UDP Peer at localhost:{self.udpRxPort} - {e}")
        self.Dispatcher = dispatcher

    def send_message(self, message: Message):
        """
        Sends an OSC packet with a given message to the peer
        - ``message``: The OSCMessage to send
        Raises:
            e: Any exceptions raised during sending are propagated upwards

        """
        if self.mode == OSCModes.TCP:
            encoded_message = self.encoder.encode(message.to_message())
            self.tcp_connection.sendall(encoded_message)
        elif self.mode == OSCModes.UDP:
            encoded_message = self.encoder.encode(message.to_message())
            self.udp_connection.sendto(encoded_message, (self.address, self.port))

    def listen_tcp(self):
        """Starts a background thread listening on TCP

        Raises:
            e: Any exceptions raised during listening are propagated upwards
        """
        print("Listening on TCP \n")
        try:
            while data := self.tcp_connection.recv(1024):
                for msg in self.decoder.decode(data):
                    ## Check if the msg is a message or a bundle
                    if isinstance(msg, OSCMessage):
                        self.Dispatcher.dispatch(msg)  # type: ignore
                    elif isinstance(msg, OSCBundle):
                        for inner_msg in msg.messages:  # type: ignore
                            self.Dispatcher.dispatch(inner_msg)  # type: ignore
        except Exception as e:
            raise e

    def listen_udp(self):
        """Starts a background thread Listening on UDP

        Raises:
            e: Any exceptions raised during listening are propagated upwards
        """
        print("Listening on UDP \n")
        try:
            while data := self.udp_connection.recv(1024):
                for msg in self.decoder.decode(data):
                    if isinstance(msg, OSCMessage):
                        self.Dispatcher.dispatch(msg)  # type: ignore
                    elif isinstance(msg, OSCBundle):
                        for inner_msg in msg.messages:  # type: ignore
                            self.Dispatcher.dispatch(inner_msg)  # type: ignore
        except Exception as e:
            raise e

    def start_listening(self):
        """Invokes the above to methods dependant on what mode is in use"""
        if self.mode == OSCModes.TCP:
            self.background = threading.Thread(
                target=self.listen_tcp, daemon=True
            )  # , args=[self.tcp_connection, self.decoder]
            self.background.start()
        elif self.mode == OSCModes.UDP:
            self.background = threading.Thread(target=self.listen_udp, daemon=True)
            self.background.start()
