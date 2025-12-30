import socket

from oscparser import OSCArg, OSCDecoder, OSCEncoder, OSCFraming, OSCMessage, OSCModes


class Peer:
    def __init__(self, address: str, port: int, mode: OSCModes = OSCModes.UDP, framing = OSCFraming.OSC10):
        self.address = address
        self.port = port
        self.message = OSCMessage
        self.args = OSCArg
        self.mode = mode
        self.framing = framing
        self.encoder = OSCEncoder(mode=self.mode, framing=self.framing)
        self.decoder = OSCDecoder(mode=self.mode, framing=self.framing)
        if self.mode == OSCModes.TCP:
            self.tcp_connection = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.tcp_connection.connect((self.address, self.port))



