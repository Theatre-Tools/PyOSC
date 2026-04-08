# Api Reference

## Peer {#peer}

```python
class Peer(address: str, port: int, mode: OSCModes, framing: OSCFraming, UDP_bind_address: str)
```

- `address`: The IP address or hostname of the remote peer.
- `port`: The port number on which the remote peer is listening.
- [`mode`](#oscmodes){ data-preview }: The transport mode, either `OSCModes.UDP` or `OSCModes.TCP`.
- [`framing`](#oscframing){ data-preview }: The OSC framing protocol, `OSCFraming.OSC10` or `OSCFraming.OSC11`.
- `UDP_bind_address`: (Optional) The local IP address to bind the UDP socket for receiving messages. Required if `mode` is `OSCModes.UDP`.

Returns a `Peer` object that can send and receive OSC messages.

The `Peer` object also returns the following attributes:

- `dispatcher`: A [`Dispatcher`](#dispatcher){ data-preview } object responsible for routing incoming messages to the appropriate handlers.

### Decorators {#peer-decorators}
The `Peer` class provides a decorator for defining event handlers that respond to specific events within the library, such as when a connection is established or when an error occurs. See [Event Handlers](./tutorials/event_handler.md){ data-preview } for more information on how to use this feature.

```python
@peer.event
def on_connect():
    print("Connected to remote peer")
```

### Methods {#peer-methods}

#### `start_listening()` {#method-start_listening}
```python
peer.start_listening()
```
Starts a background thread to listen for incoming OSC messages.

#### `send_message(message: OSCMessage)` {#method-send_message}
```python
peer.send_message(message: OSCMessage)
```

Sends an OSC message to the remote peer.

- `message`: An [`OSCMessage`](#oscmessage){ data-preview } object representing the message to be sent.

#### `stop_listening()` {#method-stop_listening}
```python
peer.stop_listening()
```
Stops the background thread that listens for incoming OSC messages.

#### Proxy Methods {#peer-proxy-methods}


##### [`Dispatcher Decorator`](#dispatcher-decorators){ data-preview } Proxy Method
The `Peer` class provides a decorator for defining handler functions that respond to specific OSC address patterns directly from the `Peer` object. This allows you to register handlers without needing to access the `Dispatcher` object separately, and ensures that handlers are properly registered and managed within the context of the `Peer`.
```python
@peer.handler("/address/pattern", validator=SomePydanticModel)
def random_handler(message: SomePydanticModel):
    # Handle the message
```

##### [`register_handler`](#method-register_handler){ data-preview } Proxy Method

The `Peer` class also provides proxy methods for the `Dispatcher` and `CallHandler`, allowing you to register handlers and make calls directly from the `Peer` object without needing to access the `Dispatcher` or `CallHandler` objects separately.

```python
peer.register_handler("/address/pattern", handler_function, validator=SomePydanticModel)
```

##### [`callHandler`](#callhandler){ data-preview } Proxy Method
Registers a handler function for a specific OSC address pattern directly from the `Peer` object.

```python
response = peer.call(
    message=OSCMessage(address='/test/ping', args=(OSCString(value='Hello_World!'),)),
    return_address='/return/address',
    validator=SomePydanticModel,
    timeout=5
)
```
Sends an OSC message and waits for a response on a specified return address directly from the `Peer` object.


## OSCMesssage {#oscmessage}

```python
class OSCMessage(address: str, args: tuple(OSCArg(value=xxx), ...))
```

- `address`: The OSC address pattern for the message (Not to be confused with the Peers IP address).
- `args`: A tuple of [`OSCArg`](#oscargs){ data-preview } objects representing the arguments of the message.


### OSCArgs {#oscargs}

```python
class OSCArg
```

Base class for all OSC argument types.
Subclasses include:

- `OSCInt`
- `OSCFloat`
- `OSCString`
- `OSCInt64`
- `OSCTimeTag`
- `OSCDouble`
- `OSCBlob`
- `OSCChar`
- `OSCSymbol`
- `OSCNil`
- `OSCRGBA`
- `OSCMidi`
- `OSCImpulse`
- `OSCArray`
- `OSCFalse`
- `OSCTrue`


## Dispatcher {#dispatcher}


The `Dispatcher` class is responsible for routing incoming OSC messages to the appropriate handler functions based on their address patterns.

### Decorators {#dispatcher-decorators}
The `Dispatcher` class provides a decorator for defining handler functions that respond to specific OSC address patterns.

```python
@dispatcher.handler("/address/pattern", validator=SomePydanticModel)
def handler_function(message: SomePydanticModel):
    # Handle the message
```

!!! Warning "Method Proxies"
    The [`Peer`](#peer){ data-preview } class provides [proxy methods](#peer-proxy-methods) for the above [`Dispatcher`](#dispatcher){ data-preview } method. It is **Highly** reccomended to use the [`Peer`](#peer){ data-preview } proxy methods instead of the [`Dispatcher`](#dispatcher){ data-preview } methods directly, as they provide better integration with the rest of the library and ensure that handlers are properly registered and managed. Using the [`Dispatcher`](#dispatcher){ data-preview } methods directly can lead to unexpected behavior and is not recommended.

### Methods {#dispatcher-methods}


#### `register_handler(address: str, handler: Callable, validator: Optional)` {#method-register_handler}
```python
dispatcher.register_handler(address: str, handler: Callable, validator: Optional)
```
Registers a handler function for a specific OSC address pattern.

- `address`: The OSC address pattern to match.
- `handler`: A callable function that will be invoked when a message with the specified address is received.
- `validator`: (Optional) A Pydantic model class used to validate and parse the incoming message.
- Returns an object of type [`Handler`](#handler){ data-preview }.

#### `remove_handler(handler: Handler)` {#method-remove_handler}

```python
dispatcher.remove_handler(handler: Handler)
```
Unregisters a handler function using the `Handler` object returned by `register_handler`.

!!! Warning "Method Proxies"
    The [`Peer`](#peer){ data-preview } class provides [proxy methods](#peer-proxy-methods) for the above [`Dispatcher`](#dispatcher){ data-preview } method. It is **Highly** reccomended to use the [`Peer`](#peer){ data-preview } proxy methods instead of the [`Dispatcher`](#dispatcher){ data-preview } methods directly, as they provide better integration with the rest of the library and ensure that handlers are properly registered and managed. Using the [`Dispatcher`](#dispatcher){ data-preview } methods directly can lead to unexpected behavior and is not recommended.

### `Handler` Object {#handler}

The handler object was implemented in version 2.0.0 in order to provide more control over registered handlers after they have been registered. When you register a handler using `register_handler`, it returns a `Handler` object that you can use to manage the handler, including removing it when neccessary.

#### Methods {#handler-methods}

`handler.unregister()`: Removes the dispatch handler from the dispatcher, perminently disabling it. This is not reversible particularly easily in the current version, so use with caution.

`handler.pause()`: Pauses the dispatch handler, preventing it from being called when messages are received. The handler can be resumed later using `handler.unpause()`.

`handler.unpause()`: Resumes a paused dispatch handler, allowing it to be called again when messages are received.



### Deprecated Methods {#dispatcher-deprecated-methods}

!!! Danger "Deprecated Methods"
    The following methods are deprecated and should be avoided. They are still available for use, but they may be removed in future versions of the library. It is recommended to use the new `Handler` object and its associated methods for managing handlers instead of these deprecated methods.

#### `add_handler(address: str, handler: Callable, validator: Optional)` {#method-add_handler}
```python
dispatcher.add_handler(address: str, handler: Callable, validator: Optional)
```
Registers a handler function for a specific OSC address pattern.

- `address`: The OSC address pattern to match.
- `handler`: A callable function that will be invoked when a message with the specified address is received.
- `validator`: (Optional) A Pydantic model class used to validate and parse the incoming message.

Returns an object of type [`Handler`](#handler){ data-preview }.


#### `remove_handler_by_address(address: str)` {#method-remove_handler}
```python
dispatcher.remove_handler_by_address(address: str)
```
Unregisters the handler function for a specific OSC address pattern.

- `address`: The OSC address pattern whose handler should be removed.

!!! Danger "The `remove_handler_by_address` method"
    The `remove_handler_by_address` method is not recommended for use, as it can lead to unexpected behavior if multiplehandlers are registered for  the same address pattern. It is better to keep track of the handler objects returned by `add_handler` and use those to remove handlers when necessary.


#### `Dispatch(message: OSCMessage)` {#method-dispatch}
```python
dispatcher.dispatch(message: OSCMessage)
```
Not to be called directly, this method is called by a background thread when a message is received. It routes the incoming message to the appropriate handler based on its address.

- `message`: An [`OSCMessage`](#oscmessage){ data-preview } object representing the incoming message.
  
## CallHandler {#callhandler}

The Call Handler has been greatly simplified in version 2.0.0, and you can call it directly from the `Peer` object, without needing to initialize a separate `CallHandler` object. This is because the Call Handler is now initialized as the default handler for the peer, so you can just call it directly.

### Methods {#callhandler-methods}

#### `call(message: OSCMessage, return_addr: str, timeout: float, validator: Optional)` {#method-call}

```python
response = peer.callHandler.call(
    message=OSCMessage(address='/test/ping', args=(OSCString(value='Hello_World!'),)),
    return_addr='/return/address',
    validator=SomePydanticModel,
    timeout=5
)
```

Sends an OSC message and waits for a response on a specified return address.

- `message`: An [`OSCMessage`](#oscmessage){ data-preview } object representing the message to be sent.
- `return_addr`: The OSC address pattern where the response is expected.
- `timeout`: The maximum time to wait for a response, in seconds.
- `validator`: (Optional) A Pydantic model class used to validate and parse the incoming response message.
- Returns: A [`CallHandler_Response`](#callhandler_response){ data-preview } object containing the response message and latency, or `None` if the call times out without receiving a valid response.

!!! Warning "Method Proxies"
    The [`Peer`](#peer){ data-preview } class provides [proxy methods](#peer-proxy-methods) for the above [`Dispatcher`](#dispatcher){ data-preview } method. It is **Highly** reccomended to use the [`Peer`](#peer){ data-preview } proxy methods instead of the [`Dispatcher`](#dispatcher){ data-preview } methods directly, as they provide better integration with the rest of the library and ensure that handlers are properly registered and managed. Using the [`Dispatcher`](#dispatcher){ data-preview } methods directly can lead to unexpected behavior and is not recommended.

##### Response

### CallHandler_Response {#callhandler_response}
```python
class CallHandler_Response:
    def __init__(self, message: OSCMessage, latency: float):
        self.message = message
        self.latency = latency
```
The `CallHandler_Response` class is a simple data structure that contains the response message and the latency of the call. The `message` attribute holds the response as an `OSCMessage` object, while the `latency` attribute indicates the time taken for the call to receive a response, measured in seconds. This does not affect validation, as the message returned within the `CallHandler_Response` is still an `OSCMessage` object that can be validated and parsed using a Pydantic model if a validator was provided in the call.

## Validators {#validators}
Validators are Pydantic models used to validate and parse incoming OSC messages before they are processed by handler functions. They ensure that the messages conform to expected formats and types.

### Creating a Validator

To create a validator, define a Pydantic model that specifies the expected structure of the OSC message. Each field in the model corresponds to an argument in the OSC message.
```python
from pydantic import BaseModel
from pyosc import OSCInt, OSCString
class PingResponse(BaseModel):
    args: tuple[OSCString]
    
    @property
    def message(self) -> str:
        return self.args[0].value
```

In this example, we define a `PingResponse` model that expects a single string argument in the OSC message. The `message` property provides a convenient way to access the string value.


## `OSCModes` Enum {#oscmodes}

There are two transport modes supported by OSC, and by extension PyOSC.

- `OSCModes.UDP`: User Datagram Protocol, a connectionless protocol that is faster but does not guarantee message delivery.
- `OSCModes.TCP`: Transmission Control Protocol, a connection-oriented protocol that guarantees message delivery but is slower due to the overhead of establishing and maintaining a connection.

TCP is generally preferred for applications where message delivery is critical, while UDP may be suitable for applications that require low latency and can tolerate some message loss. TCP is also simpler to work with, as you know when a connection is established, and you don't have to manage ports for receiving messages separately.

## `OSCFraming` Enum {#oscframing}
OSC messages can be framed in different ways depending on the version of the OSC protocol being used.
- `OSCFraming.OSC10`: The original OSC 1.0 framing protocol.
- `OSCFraming.OSC11`: The updated OSC 1.1 framing protocol,

The two versions of the specification can be found here:

- [OSC 1.0 Specification](https://opensoundcontrol.stanford.edu/spec-1_0.html)
- [OSC 1.1 Specification](https://opensoundcontrol.stanford.edu/files/2009-NIME-OSC-1.1.pdf)

When using version 1.1 and UDP transport, messages are actually exactly the same as version 1.0, however when using TCP transport, this are a little bit different.