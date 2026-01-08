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

- `message`: An [`OSCMessage`](#oscmessage) object representing the message to be sent.

#### `stop_listening()` {#method-stop_listening}
```python
peer.stop_listening()
```
Stops the background thread that listens for incoming OSC messages.


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

```python
class Dispatcher()
```
The `Dispatcher` class is responsible for routing incoming OSC messages to the appropriate handler functions based on their address patterns.

### Methods {#dispatcher-methods}

#### `add_handler(address: str, handler: Callable, validator: Optional)` {#method-add_handler}
```python
dispatcher.add_handler(address: str, handler: Callable, validator: Optional)
```
Registers a handler function for a specific OSC address pattern.

- `address`: The OSC address pattern to match.
- `handler`: A callable function that will be invoked when a message with the specified address is received.
- `validator`: (Optional) A Pydantic model class used to validate and parse the incoming message.

#### `remove_handler(address: str)` {#method-remove_handler}
```python
dispatcher.remove_handler(address: str)
```
Unregisters the handler function for a specific OSC address pattern.

- `address`: The OSC address pattern whose handler should be removed.

#### `add_default_handler(handler: Callable)` {#method-default_handler}
```python
dispatcher.add_default_handler(handler: Callable)
```
Registers a default handler function that will be invoked when no other registered handlers match the incoming message's address.

- `handler`: A callable function that will be invoked for unmatched messages.

!!! warning

    It is likely the default handler will be deprecated in a future version of PyOSC, to be replaced with a default CallHandler that can be customized or overwritten.

#### `Dispatch(message: OSCMessage)` {#method-dispatch}
```python
dispatcher.dispatch(message: OSCMessage)
```
Not to be called directly, this method is called by a background thread when a message is received. It routes the incoming message to the appropriate handler based on its address.

- `message`: An [`OSCMessage`](#oscmessage){ data-preview } object representing the incoming message.
  
## CallHandler {#callhandler}

```python
caller = CallHandler(peer)

```
The `CallHandler` class is a specialized handler that facilitates sending OSC messages and waiting for responses

- `peer`: A [`Peer`](#peer){ data-preview } object used to send and receive messages.

!!! warning

    The `CallHandler` will likely change in a future version of PyOSC, and will likely be the initialized as the default handler when a [`Peer`](#peer){ data-preview } object is created.

### Methods {#callhandler-methods}

#### `call(message: OSCMessage, return_addr: str, timeout: float, validator: Optional)` {#method-call}
```python
response = caller.call(
    message: OSCMessage,
    return_addr: str,
    timeout: float,
    validator: Optional
)
```
Sends an OSC message and waits for a response on a specified return address.

- `message`: An [`OSCMessage`](#oscmessage){ data-preview } object representing the message to be sent.
- `return_addr`: The OSC address pattern where the response is expected.
- `timeout`: The maximum time to wait for a response, in seconds.
- `validator`: (Optional) A Pydantic model class used to validate and parse the incoming response message.
- Returns: A `BaseModel` object containing the response message, or `None` if the timeout is reached without receiving a response.

##### Response
The response returned by the `call` method is an instance of the Pydantic model specified by the `validator` parameter. This model will contain the parsed arguments of the response message, allowing for easy access to the data contained within the OSC message.

If no `validator` is provided, the raw [`OSCMessage`](#oscmessage){ data-preview } object will be returned.


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

### Using a Validator

When registering a handler with the `Dispatcher`, you can specify a validator to ensure that incoming messages are validated before being passed to the handler function.

```python
peer.dispatcher.add_handler("/test/out/ping", ping_handler, validator=PingResponse)
```

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