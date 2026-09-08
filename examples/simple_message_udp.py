from pyosc import OSCFraming, OSCMessage, OSCTransport, Peer
from pyosc.types import OSCInt, OSCString

peer = Peer(
    remote_address="127.0.0.1",
    remote_port=8001,
    transport=OSCTransport.UDP,
    framing=OSCFraming.OSC10,
    bind_ip="127.0.0.1",
    bind_port=9002,
)

message = OSCMessage(
    address="/test/message",
    args=(
        OSCInt(value=42),
        OSCString(value="Hello_world!"),
    ),
)
peer.send_message(message)
