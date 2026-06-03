from select import select

from .exceptions import PeerConnectionError, PeerListenerError


def  _tcp_listener(self):
    try:
        if not self.connected.is_set():
            raise PeerConnectionError("TCP listener cannot start until a client has connected")
        while self.stop_flag.is_set() is False:
            read, _write, _exec = select([self.tcp_connection], [], [], 0.01)
            for sock in read:
                data = sock.recv(2**16)
                if data == b"":
                    self.tcp_connection.close()
                    self._emit_connection_state(False)
                    return
                for msg in self.decoder.decode(data):
                    self.dispatcher.dispatch(msg)
        self.tcp_connection.close()
    except Exception as e:
        listener_error = PeerListenerError(f"TCP listener failed for {self.address}:{self.port} - {e}")
        self._emit_error(listener_error)
        self._emit_connection_state(False)
