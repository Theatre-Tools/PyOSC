# Event Handlers
In version 1.1.0, we introduced a new method of dealing with events and errors that happen within the library. It's more intuative and consistent, and allows for more flexibility in terms of how you can handle events and errors. This section of the documentation will cover how to use the new event handling system, as well as some examples of how to use it.

## Decorators
The new event handling system is based on decorators, which are a powerfull and flexible way to define advanced functionality in a clean and readable way. Here's an example of how you might use a decorator to define a function that runs every time a peer becomes connected:

```python
from pyosc import Peer, OSCModes, OSCFraming

peer = Peer("127.0.0.1", 3032, mode=OSCModes.TCP, framing=OSCFraming.OSC11)

@peer.event
def on_connect(peer: Peer):
    print(f"Peer {peer} has connected!")
```

In this example, we define a function that prints a message when the peer connects. The `@peer.event` decorator combined with the function name tells the library that this function should be called whenever the peer becomes connected.

Below is a table of currently supported events that you can use with the `@peer.event` decorator:

| Event Name | Aliases | Description | Arguments |
|------------|---------|-------------|-----------|
| `on_connect` | `on_connection` | Called when a peer becomes connected | `peer` The peer object that connected |
| `on_disconnect` | `on_disconnection` | Called when a peer becomes disconnected | `peer` The peer object that disconnected |
| `on_error ` | `on_exception` | Called when an error occurs within the library | `peer` The peer object that triggered the error, `error` The exception object that was raised |