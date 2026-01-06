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