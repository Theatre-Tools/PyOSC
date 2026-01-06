from pyosc import Dispatcher, OSCFraming, OSCInt, OSCMessage, OSCModes, OSCString, Peer

dispatcher = Dispatcher()
peer = Peer(
    "127.0.0.1",
    8001,
    dispatcher=dispatcher,
    mode=OSCModes.UDP,
    framing=OSCFraming.OSC10,
    udp_rx_address="127.0.0.1",
    udp_rx_port=9001,
)
message = OSCMessage(
    address="/test/message",
    args=(
        OSCInt(value=42),
        OSCString(value="Hello"),
    ),
)
peer.send_message(message)
