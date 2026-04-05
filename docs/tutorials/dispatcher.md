# The Dispatcher

The [`Dispatcher`](../api_reference.md#dispatcher){ data-preview } object in PyOSC is what routes incoming OSC messages based on their address. It's implementation is simple and efficient, allowing you to easily register handler based on methods, addresses and pydanntic models.

## Creating a Dispatcher

Dispatchers no longer need to be explicitly created, as they are now automatically initialized when you create a [`Peer`](../api_reference.md#peer){ data-preview } object. However, if you need to create one manually, you can do so like this:

```python
from pyosc import Dispatcher

dispatcher = Dispatcher()
```

## Registering Handlers

!!! Danger "The default handler"
    The concept of a default handler hasn't existed for a few versions at this point, so I think it is appropriate to remove it from the documentation. However, I will at this time reccomend against using the `/*` wildcard as a replacement, as it is against specification and this workaround will be removed in version 2.0.0. If you do need this functionality, I will be implementing a replacement method for this functionality in a comming release pre 2.0.0, as 2.0.0 will contain multiple Major breaking changes.

### Registering Handlers {#handlers}

In addition to the default handler, you can register handlers for specific OSC addresses. This allows you to drop or ignore messages from certain addresses, as well as process information from others.

Here's an example of what a handler specific addresss might look like:

```python

def ping_handler(message): #(1)!
    print(f"Received a ping message! {message.args}") #(2)!

peer.dispatcher.add_handler("/test/out/ping", ping_handler) #(3)!

```

1. The `ping_handler` function is defined to handle messages sent to the `/test/out/ping` address.
2. Inside the handler, we print out the arguments of the received ping message.
3. The `ping_handler` function is registered to handle messages sent to the `/test/out/ping` address using the `add_handler` method of the `dispatcher` attribute of the `peer` object.

Dispatch handlers can be registered and destroyed at any time, this is because when a message is received, the dispatcher checks against it's list of handlers to see if any match the incoming message's address. As long as the handler is registered when the message arrives, it will be called.

### Validators {#validators}

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

peer.dispatcher.add_handler("/test/out/ping", ping_handler, validator=PingResponse) #(5)!

```

1. We import `BaseModel` from the `pydantic` library to create a validator model.
2. We define a `PingResponse` model that specifies the expected structure of the incoming message
3. We define a property `message` that extracts the string value from the first argument of the message.
4. The `ping_handler` function is defined to accept a `PingResponse` object, which will be validated before being passed to the handler.
5. The `ping_handler` function is registered to handle messages sent to the `/test/out/ping` address, this time with the `PingResponse` model as its validator.

## Examples

Here is a complete example that demonstrates the use of a dispatcher with both a default handler and an address-specific handler with a validator:

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


def default_handler(message):
    with open("messages.log", "a") as log_file:
        log_file.write(f"Received a message on address:{message.address} with args: {message.args}\n") #(4)!

def ping_handler(message: PingResponse):
    print(f"Received a ping message with response: {message.message}") #(7)!

peer.dispatcher.add_default_handler(default_handler)
peer.dispatcher.add_handler("/test/out/ping", ping_handler, validator=PingResponse) #(5)!
peer.start_listening() #(6)!
```

1. A `Peer` object is created to handle OSC messages over TCP on localhost at port 3032.
2. A `PingResponse` pydantic model is defined to validate incoming ping messages.
3. A property `message` is defined to extract the string value from the first argument of
4. The `default_handler` function logs all received messages to a file named `messages.log`.
5. The `ping_handler` function is registered to handle messages sent to the `/test/out/ping` address, with the `PingResponse` model as its validator.
6. The `start_listening` method is called on the `Peer` object to begin receiving messages.
7. The `ping_handler` function prints the response message when a valid ping message is received.
