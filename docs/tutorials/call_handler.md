# Call Handlers

In PyOSC, a [`CallHandler`](../api_reference.md#callhandler){ data-preview } is a kind of handler that is designed for sending a message and expecting or waiting for a response.
This is particularly useful for request-response patterns, where you send a message to a remote peer and want to handle the response in a structured way.

They function in a very similar way to dispatch handlers, and actually replace the need for writing a default handler, as the call handler will handle the response for you.

## Creating a Call Handler
To create a `CallHandler`, you need to define a handler function that will process the response message. You can also define a validator function to ensure that the incoming message is of the expected type.

In this simple example we will create a call handler, assuming that you have already created a [`Peer`](../api_reference.md#peer){ data-preview } object called `peer`.

```python
from pyosc import CallHandler

call_handler = CallHandler(peer) #(1)!
peer.dispatcher.add_default_handler(call_handler) #(2)!
```

1. The `CallHandler` is instantiated with the `peer` object, which allows it to send messages through that peer.
2. The `call_handler` is registered as the default handler for the `peer`'s dispatcher. This means that it will handle incoming messages that do not match any other registered handlers.

## Using the Call Handler
Once you have created a `CallHandler`, you can use it to send messages and wait for responses. You can specify a validator to ensure that the response message is of the expected type.

Here's an example of how to use the `CallHandler` to send a message and wait for a response:

```python
from pyosc import OSCMessage, OSCString

response = call_handler.call(
    OSCMessage(address="/test/ping", args=(OSCString(value="Hello_world!"),)),
    return_addr="/test/out/ping",
    timeout=10.0,
)  # (1)!
if response:
    print(response.message)  # (2)!
```

1. The [`call`](../api_reference.md#callhandler#call){ data-preview } method of the [`call_handler`](../api_reference.md#callhandler){ data-preview } is used to send an [`OSCMessage`](../api_reference.md#oscmessage){ data-preview } to the address `/test/ping`, with a string argument. The `return_addr` parameter specifies the address where the response is expected, and the `timeout` parameter specifies how long to wait for a response.
2. If a response is received within the timeout period, it is printed to the console.