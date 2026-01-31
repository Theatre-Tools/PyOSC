from pyosc import OSCFraming, OSCInt, OSCMessage, OSCModes, OSCString, Peer

peer = Peer(
    "127.0.0.1",
    8001,
    mode=OSCModes.UDP,
    framing=OSCFraming.OSC10,
    udp_rx_address="127.0.0.1",
    udp_rx_port=9001,
)
message = OSCMessage(
    address="/test/message",
    args=(
        OSCInt(value=42),
        OSCString(value="Hello_world!"),
    ),
)
peer.send_message(message)
