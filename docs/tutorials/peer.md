# The Peer Object
The [`Peer`](../api_reference.md#peer){ data-preview } object is the central component of PyOSC, responsible for managing the sending and receiving of OSC messages over a network. It encapsulates the network connection details, message dispatching, and provides an interface for interacting with OSC messages.

## Initialization
To create a `Peer` object, you need to provide the following parameters:

- `address`: The IP address or hostname of the remote peer.
- `port`: The port number on which the remote peer is listening.
- `mode`: The transport mode, either `OSCModes.UDP` or `OSCModes.TCP`.
- `framing`: The OSC framing protocol, `OSCFraming.OSC10` or `OSCFraming.OSC11`.

Example:

=== "TCP example"
    ```python
    from pyosc import Peer, OSCModes, OSCFraming
    peer = Peer(
        "127.0.0.1",
        3032,
        mode=OSCModes.TCP,
        framing=OSCFraming.OSC11
    )
    ```
=== "UDP example"
    ```python
    from pyosc import Peer, OSCModes, OSCFraming
    peer = Peer(
        "127.0.0.1",
        8001,
        mode=OSCModes.UDP,
        framing=OSCFraming.OSC11,
        UDP_bind_address="127.0.0.1",
        UDP_bind_port=8002
    )
    ```
    
    !!! Note
        When using UDP, it is important to specify the `UDP_bind_address` and `UDP_bind_port` to bind the socket for receiving messages.

## Sending Messages
To send an OSC message, you must first create an [`OSCMessage`](../api_reference.md#oscmessage){ data-preview } object.
Example:

```python
from pyosc import OSCMessage, OSCInt, OSCString
message = OSCMessage(
    address="/test/ping", #The address to send the message to
    args=(
        OSCString(value="Hello, World!"), ## Arguments take a value
  )# A tuple of `OSCArgs`
 )
```


