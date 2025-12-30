import socket
import threading
import time

from oscparser import OSCArg, OSCDecoder, OSCEncoder, OSCFraming, OSCMessage, OSCModes


class Peer:
    def __init__(self, address: str, port: int, mode: OSCModes = OSCModes.UDP, framing=OSCFraming.OSC10, udp_rx_port: int = 8001):
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
            self.tcp_connection = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.tcp_connection.connect((self.address, self.port))
        elif self.mode == OSCModes.UDP:
            self.udp_connection = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.udp_connection.bind(('localhost', self.udpRxPort))

    def send_message(self, message: OSCMessage):
        """
        Sends an OSC packet with a given message to the peer
        """
        if self.mode == OSCModes.TCP:
            encoded_message = self.encoder.encode(message)
            self.tcp_connection.sendall(encoded_message)
        elif self.mode == OSCModes.UDP:
            encoded_message = self.encoder.encode(message)
            self.udp_connection.sendto(encoded_message, (self.address, self.port))

    def listen_tcp(self):
        print("listening on TCP")
        try:
            while data := self.tcp_connection.recv(1024):
                for msg in self.decoder.decode(data):
                    print(f"{msg}")
        except Exception as e:
            raise e

    def listen_udp(self):
        print("Listening on UDP")
        ## Listens on a UDP socket on the port specifies (Mimmicks behavure of the TCP listener)
        try:

            while data :=self.udp_connection.recvfrom(1024):
                print(data)
        except Exception as e:
            raise e



    ## Have a second thread listening for incoming messages on a different thread
    def start_listening(self):
        if self.mode == OSCModes.TCP:
            background = threading.Thread(target=self.listen_tcp, daemon=True)  # , args=[self.tcp_connection, self.decoder]
            background.start()
            for i in range(100):
                print("I AM THE CHOSEN ONE1")
                time.sleep(10)
        elif self.mode == OSCModes.UDP:
            background = threading.Thread(target=self.listen_udp, daemon=True)
            background.start()
            for i in range(100):
                print("Main thread")
                time.sleep(10)
