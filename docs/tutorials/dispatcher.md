# The Dispatcher

The [`Dispatcher`](../api_reference.md#dispatcher){ data-preview } object in PyOSC is what routes incoming OSC messages based on their address. It's implementation is simple and efficient, allowing you to easily register handler based on methods, addresses and pydanntic models.

## Creating a Dispatcher
Dispatchers no longer need to be explicitly created, as they are now automatically initialized when you create a [`Peer`](../api_reference.md#peer){ data-preview } object. However, if you need to create one manually, you can do so like this:

```python
from pyosc import Dispatcher

dispatcher = Dispatcher()
```

## Registering Handlers

### The Default Handler
In PyOSC handlers are registed by the address for which they are handling messages for. There is only one dispatch handler that doesn't have an address assigned to it, and that is the [`default handler`](../api_reference.md#Dispatcher#default_handler){ data-preview }, which is called when no other handlers match the incoming message's address.

Let's make a simple example, that registers a default handler, and prints the message. The default [`validator`](../api_reference.md#Dispatcher#default_validator){ data-preview } will accept all OSCMessages.

We will assume you have already created a [`Peer`](../api_reference.md#peer){ data-preview } object called `peer`.

```python

def default_handler(message):#(1)!
    print(f"Received a message on address:{message.address} with args: {message.args}") #(2)!

peer.dispatcher.add_default_handler(default_handler) #(3)!
```

1. The `default_handler` function is defined to be parsed a single parameter, `message`, which is expected to be an [`OSCMessage`](../api_reference.md#oscmessage){ data-preview } object.
2. Inside the handler, we print out the address and arguments of the received message.
3. The `default_handler` function is registered as the default handler using the `add_default_handler` method of the `dispatcher` attribute of the `peer` object.

To receive messages, simply call the `start_listening` method on the `Peer` object:

```python
peer.start_listening()
```

Here is a full example:

```python
from pyosc import Peer, OSCMessage, OSCModes, OSCFraming

peer = Peer(
    "127.0.0.1",
    3032,
    mode=OSCModes.TCP,
    framing=OSCFraming.OSC11,
)

def default_handler(message):
    print(f"Received a message on address:{message.address} with args: {message.args}")

peer.dispatcher.add_default_handler(default_handler)
peer.start_listening()
```

### Registering Address-Specific Handlers
In addition to the default handler, you can register handlers for specific OSC addresses. This allows you to drop or ignore messages from certain addresses, as well as process information from others.

Here's an example of what a handler specific addresss might look like:

```python

def ping_handler(message): #(1)!
    print(f"Received a ping message! {message.args}") #(2)!

peer.dispatcher.add_handler("/test/ping", ping_handler) #(3)!

```

1. The `ping_handler` function is defined to handle messages sent to the `/test/ping` address.
2. Inside the handler, we print out the arguments of the received ping message.
3. The `ping_handler` function is registered to handle messages sent to the `/test/ping` address using the `add_handler` method of the `dispatcher` attribute of the `peer` object.

### Validators
When registering handlers, you can also provide an optional `validator`. A validator is a pydantic model that is used to validate incoming messages before they are passed to the handler. If the message does not conform to the validator, it will be rejected and not processed by the handler.

Here's an example of registering a handler with a validator:

```python
from pydantic import BaseModel #(1)!

class PingResponse(BaseModel): #(2)!
    args: tuple[OSCString]
    
    @property
    def message(self) -> str:
        return self.args[0].value #(3)!

def ping_handler(message: PingResponse): #(4)!
    print(f"Received a ping message with response: {message.message}")

peer.dispatcher.add_handler("/test/ping", ping_handler, validator=PingResponse) #(5)!

```

1. We import `BaseModel` from the `pydantic` library to create a validator model.
2. We define a `PingResponse` model that specifies the expected structure of the incoming message
3. We define a property `message` that extracts the string value from the first argument of the message.
4. The `ping_handler` function is defined to accept a `PingResponse` object, which will be validated before being passed to the handler.
5. The `ping_handler` function is registered to handle messages sent to the `/test/ping` address, this time with the `PingResponse` model as its validator.