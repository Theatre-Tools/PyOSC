import socket


def listen_tcp(connection, decoder):
    if not isinstance(connection, socket.socket):
        raise TypeError("Connection must be instance of type: Socket")
    try:
        while data := connection.recv(1024):
            for msg in decoder.decode(data):
                print(msg)
    except Exception as e:
        raise e
