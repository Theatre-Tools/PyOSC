# Call Handlers {#CallHandlers}

In PyOSC, a [`CallHandler`](../api_reference.md#callhandler){ data-preview } is a kind of handler that is designed for sending a message and expecting or waiting for a response.
This is particularly useful for request-response patterns, where you send a message to a remote peer and want to handle the response in a structured way.

They function in a very similar way to dispatch handlers, and actually replace the need for writing a default handler, as the call handler will handle the response for you.

In versions after 2.0.0, the `CallHandler` is now integrated directly into the peer class, and initialized automatically when a peer is created. This means you can use the call handler without the clutter of having to create the call handler.

## Using the Call Handler {#Using-CallHandler}
The `CallHandler` can be accessed via `peer.callHandler`, however there is very little utility to doing this, as all user facing methods are exposed via proxy methods of the `Peer` class. This means you can call messages and wait for responses directly from the `Peer` object, without having to interact with the `CallHandler` directly. Here's an example of how to use the call handler to send a message and wait for a response:

```python
from pyosc import OSCMessage, OSCString

response = peer.call(
    OSCMessage(address="/test/ping", args=(OSCString(value="Hello_world!"),)),
    return_addr="/test/out/ping",
    timeout=5.0,
)  # (1)!
if response:
    print(response.message)  # (2)!
    print(f"Round-trip latency: {response.latency:.2f} seconds")  # (3)!
```

1. The [`call`](../api_reference.md#callhandler-proxy-method){ data-preview } method of the [`Peer`](../api_reference.md#peer){ data-preview } is used to send an [`OSCMessage`](../api_reference.md#oscmessage){ data-preview } to the address `/test/ping`, with a string argument. The `return_addr` parameter specifies the address where the response is expected, and the `timeout` parameter specifies how long to wait for a response.
2. If a response is received within the timeout period, it is printed to the console.
3. The round-trip latency is also printed, showing how long it took for the response to be received after the message was sent.

In this example, we send a ping message to the `/test/ping` address, and wait for a response on the `/test/out/ping` address. If a response is received within 5 seconds, it is printed to the console.

Starting in version 2.0.0, the call handler returns a [`CallResponse`](../api_reference.md#callresponse){ data-preview } object. This contains the message, and a latency paramenter that indicates how long it took for the response to be received. This allows you to easily measure the round-trip time of your messages, which can be useful for debugging and performance monitoring.

##### Multiple Responses {#Multiple-Responses}
The `call` method also supports waiting for multiple responses to a single message. This can be useful in situations where you expect multiple responses to a single message. To wait for multiple responses, you can use the `responses` parameter of the `call` method. It should be noted that the `responses` parameter specifies the ***Maximum*** number of responses to wait for. Here's an example:
```python
responses = peer.call(
    OSCMessage(address="/test/ping", args=(OSCString(value="Hello_world!"),
    )),
    return_addr="/test/out/ping",
    timeout=10.0,
    responses=3,  #(1)!
)

if isinstance(responses, list):
    for response in responses:
        print(response.message) #(2)!
        print(f"Round-trip latency: {response.latency:.2f} seconds") #(3)!

```

1. The `responses` parameter is set to 3, which means that the `call` method will wait for up to 3 responses to be received on the return address before returning. If 3 responses are received, they will be returned as a list of `CallResponse` objects.
2. If multiple responses are received, they are printed to the console in a loop.

If multiple responses are expected, the `call` method will return a list of `CallHandler_Response` objects, each containing a response message and its corresponding latency. If only a single response is expected, it will return a single `CallHandler_Response` object. If no response is received within the timeout period, it will return `None`.

Responses defaults to one. If you only expect a single response, there is no reason to specify it manually.

##### Prefixes {#Prefixes}
The `prefix` parameter is a really powerfull yet simple way to handle multiple messages coming in, while interfacing with a peer like a traditional API. It allows you, and more importantly, the validator to ignore the first x number of messages coming in. This was added out of neccesity to enable support for features in a dependant library.
For example, if you are interfacing with a piece of software that sends mutliple argument schemas on a single address. If you have an address that sends an inital message to say how many items there are, and then sends follow up messages with more detailed information on those actual items. A validator would fail as it would initally reject the first message, using prefixes is a stopgap that allows you to simply siphon off the first message.

!!! Note
    The `responses` parameter ***Includes*** any messages that may be dropped by the `prefix` parameter. It may be neccesary to adjust the `responses` parameter accordingly.


```python
responses = peer.call(
    OSCMessage(address="/test/ping", args=(OSCString(value="Hello_world!"),
    )),
    return_addr="/test/out/ping",
    timeout=10.0,
    responses=3,
    prefix=1,  #(1)!
)
if isinstance(responses, list):
    for response in responses:
        print(response.message) #(2)!
        print(f"Round-trip latency: {response.latency:.2f} seconds") #(3)!
```

1. The `prefix` parameter is set to 1, which means that the first message received on the return address will be ignored, and the `call` method will wait for the next 2 messages to be received before returning. This can be useful in situations where you expect a certain number of messages to be sent before the actual response messages are sent.


### Using [Validators](./dispatcher.md#validators){ data-preview }
You can also specify a validator when calling a message to ensure that the response message is of the expected type. Here's an example:

```python
from pydantic import BaseModel #(5)!
from pyosc import OSCString

class PingResponse(BaseModel):
    args: tuple[OSCString]
    
    @property
    def message(self) -> str:
        return self.args[0].value #(1)!


response = peer.call(
    OSCMessage(address="/test/ping", args=(OSCString(value="Hello_world!"),
    )),
    validator=PingResponse,  #(2)!
    return_addr="/test/out/ping",
    timeout=10.0,
)

if response:
    print(response.message.message) #(3)!
    print(f"Round-trip latency: {response.latency:.2f} seconds") #(4)!
```

1. A `PingResponse` model is defined using Pydantic, which specifies that the response message should have a tuple of `OSCString` arguments. A property `message` is defined to extract the string value from the first argument of the response message.
2. When calling the message, the `validator` parameter is set to the `PingResponse` model.
3. model. This means that when a response is received, it will be validated against the `PingResponse` model before being passed to the caller. If the response does not conform to the model, it will be rejected and an error will be raised.
4. The round trip latency is printed as before, allowing you to measure the time it took for the response to be received.
5. We import the `BaseModel` class from Pydantic, which is used to define the `PingResponse` model. This allows us to easily validate the structure of the response message and extract the relevant information in a structured way.

In this example, we define a `PingResponse` model that specifies the expected structure of the response message. When calling the message, we provide this model as the validator. If the response message conforms to the model, it is printed to the console.

### Call Response {#CallResponse}

The `CallHandler` returns a `CallHandler_Response` object, which contains the response, in the form of iether a BaseModel instance or an [`OSCMessage`](../api_reference.md#oscmessage){ data-preview }, and the latency of the round trip. This allows you to easily access the response message and measure the time it took for the response to be received. Having the latency information can be very useful for a vareity of things, including debugging, physical network configurations, performance monitoring, and simple ping command implementations.

The Latency is measured from when the message is sent to the peer, all the way to where the message is received, dispatched and validated. The time is calculated just before the object is returned from the caller.



## Examples {#CallHandler-Examples}

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
peer.start_listening() #(7)!


class PingResponse(BaseModel):
    args: tuple[OSCString] #(2)!
    
    @property
    def message(self) -> str:
        return self.args[0].value #(3)!

response = peer.call(
    OSCMessage(address="/test/ping", args=(OSCString(value="Hello_world!"),
    )),
    validator=PingResponse,
    return_addr="/test/out/ping",
    timeout=10.0,
) #(4)!

if response:
    print(response.message.message) #(5)!
    print(f"Round-trip latency: {response.latency:.2f} seconds") #(6)!
    

```

1. We create a `Peer` object that listens on localhost at port 3032 using TCP and OSC 1.1 framing.
2. We define a `PingResponse` model that specifies the expected structure of the incoming message. In this case, we expect a tuple of `OSCString` arguments.
3. We define a property `message` that extracts the string value from the first argument of the message. This allows us to easily access the response message in a structured way.
4. We use the `peer.call` method to send a ping message to the `/test/ping` address, and specify the `PingResponse` model as the validator for the expected response. We also specify the `return_addr` where we expect the response to be sent, and a timeout for how long to wait for the response.
5. If a response is received within the timeout period, we print the response message to the console.
6. We also print the round-trip latency, which indicates how long it took for the response to be received after the message was sent.
7. We start the peer's listening loop, allowing it to receive and process incoming messages. This is necessary for the peer to be able to receive the response to our call message.

