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

1. The [`call`](../api_reference.md#method-call){ data-preview } method of the [`call_handler`](../api_reference.md#callhandler){ data-preview } is used to send an [`OSCMessage`](../api_reference.md#oscmessage){ data-preview } to the address `/test/ping`, with a string argument. The `return_addr` parameter specifies the address where the response is expected, and the `timeout` parameter specifies how long to wait for a response.
2. If a response is received within the timeout period, it is printed to the console.

In this example, we send a ping message to the `/test/ping` address, and wait for a response on the `/test/out/ping` address. If a response is received within 10 seconds, it is printed to the console.

### Using [Validators](./dispatcher.md#validators){ data-preview }
You can also specify a validator when calling a message to ensure that the response message is of the expected type. Here's an example:

```python
from pydantic import BaseModel
from pyosc import OSCString

class PingResponse(BaseModel):
    args: tuple[OSCString]
    
    @property
    def message(self) -> str:
        return self.args[0].value


response = call_handler.call(
    OSCMessage(address="/test/ping", args=(OSCString(value="Hello_world!"),
    )),
    validator=PingResponse,  #(1)!
    return_addr="/test/out/ping",
    timeout=10.0,
)

if response:
    print(response.message) 
```

1. The `validator` parameter is set to the `PingResponse` pydantic model, which defines the expected structure of the response message. If the response message does not conform to this model, it will be rejected.

In this example, we define a `PingResponse` model that specifies the expected structure of the response message. When calling the message, we provide this model as the validator. If the response message conforms to the model, it is printed to the console.

## Examples

Here is a complete example that demonstrates the use of a `CallHandler` to send a ping message and handle the response:

```python
from pyosc import Peer, OSCMessage, OSCModes, OSCFraming, OSCString
from pydantic import BaseModel

peer = Peer(
    "127.0.0.1",
    3032,
    mode=OSCModes.TCP,
    framing=OSCFraming.OSC11,
) #(1)!

class PingResponse(BaseModel):
    args: tuple[OSCString] #(2)!
    
    @property
    def message(self) -> str:
        return self.args[0].value #(3)!

call_handler = CallHandler(peer)
response = call_handler.call(
    OSCMessage(address="/test/ping", args=(OSCString(value="Hello_world!"),
    )),
    validator=PingResponse,
    return_addr="/test/out/ping",
    timeout=10.0,
) #(4)!

if response:
    print(response.message) #(5)!
    
peer.dispatcher.add_default_handler(call_handler) #(6)!
peer.start_listening() #(7)!

```

1. A `Peer` object is created to manage the network connection.
2. A `PingResponse` model is defined to specify the expected structure of the response message
3. A property `message` is defined to extract the string value from the first argument of the response message.
4. A `CallHandler` is created and used to send a message and wait for a response, with the `PingResponse` model as the validator.
5. If a response is received, the message is printed to the console.
6. The `call_handler` is registered as the default handler for the `peer`'s dispatcher.
7. The `peer` starts listening for incoming messages.

