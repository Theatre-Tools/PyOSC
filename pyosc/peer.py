import socket
import threading
import time

from oscparser import OSCArg, OSCDecoder, OSCEncoder, OSCFraming, OSCMessage, OSCModes

from .listener import listen_tcp


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

    def send_message(self, message: OSCMessage):
        """
        Sends an OSC packet with a given message to the peer
        """
        encoded_message = self.encoder.encode(message)
        self.tcp_connection.sendall(encoded_message)

    ## Have a second thread listening for incoming messages on a different thread
    def start_listening(self):
        background = threading.Thread(target=listen_tcp, daemon=True, args=[self.tcp_connection, self.decoder])
        background.start()
        for i in range(100):
            print("I AM THE CHOSEN ONE1")
            time.sleep(10)
