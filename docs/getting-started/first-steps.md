# First Steps

This is a quick guide to get you started with PyOSC, you should follow the API docs and examples for more detailed information on how to use the library.


## Sending Your First OSC Message
To send your first OSC message using PyOSC, you can use the following example code:

```py
from pyosc import Peer, OSCMessage, OSCModes, OSCFraming, OSCInt, OSCString

peer = Peer(
    "127.0.0.1",
    3032,
    mode=OSCModes.TCP,
    framing=OSCFraming.OSC11,
)
message = OSCMessage(
    address="/test/message",
    args=(
        OSCInt(value=42),
        OSCString(value="Hello_World!"),
    )
)
peer.send_message(message)
```
The above example creates a [`Peer`](../api_reference.md#peer){ data-preview } object, using the TCP mode, and framing from OSC version 1.1. It then constructs a [`OSCMessage`](../api_reference.md#oscmessage){ data-preview } with the address `/test/message` and two arguments:

1. An integer with the value `42`
2. A string with the value `Hello_World!`

Finally, it sends the message using the [`send_message`](../api_reference.md#peer){ data-preview } method, of the [`Peer`](../api_reference.md#peer){ data-preview } object.