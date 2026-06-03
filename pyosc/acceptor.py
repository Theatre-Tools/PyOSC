import socket
import threading

from oscparser import OSCTransport

from .connection import _tcp_listener


def _accept_tcp(peer):
    connection, address = peer.bind.accept()
    peer.tcp_connection = connection
    peer.client_address = address
    peer._emit_connection_state(True)
    peer.listener_background = threading.Thread(target=_tcp_listener, args=(peer,), daemon=True)
    peer.listener_background.start()


def _bind_TCP(peer):
    peer.bind = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    peer.bind.bind((peer.bind_address, peer.bind_port))
    peer.bind.listen(1)


def _accept_connection(peer):
    if peer.transport == OSCTransport.TCP:
        _bind_TCP(peer)
        peer.accept_background = threading.Thread(target=_accept_tcp, args=(peer,), daemon=True)
        peer.accept_background.start()
        return None
    else:
        raise NotImplementedError("Only TCP acceptor role is currently implemented")
