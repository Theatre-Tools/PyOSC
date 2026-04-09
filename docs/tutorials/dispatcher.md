# The Dispatcher

The [`Dispatcher`](../api_reference.md#dispatcher){ data-preview } object in PyOSC is what routes incoming OSC messages based on their address. It's implementation is simple and efficient, allowing you to easily register handler based on methods, addresses and pydanntic models.
The dispatcher's core methods are exposed via [proxy methods](../api_reference.md#peer){ data-preview } in the `peer` class. 

## Registering Handlers

### `@peer.handler` Decorator {#peer-handler-decorator}

There are currently two ways to register handlers. The first way is to use the `peer.handler` decorator, which is a convenient way to register a handler function for a specific address pattern. The second way is to use the `peer.register_handler` method to register a handler function for a specific address. Examples below:

```python

@peer.handler("/test/out/ping") #(1)!
def ping_handler(message):
    print(f"Received a ping message with args: {message.args}")

```

1. The `peer.handler` decorator is used to register the `ping_handler` function as a handler for messages sent to the `/test/out/ping` address. Whenever a message with this address is received, the `ping_handler` function will be called with the message as its argument.

##### Using Validators with Decorators

These can also be used with [`validators`](#validators){ data-preview } to ensure that incoming messages are validated before being passed to the handler function, and can be parsed programatically within the handler.

```python
from pydantic import BaseModel

class PingResponse(BaseModel):
    args: tuple[OSCString]

    @property
    def message(self) -> str:
        return self.args[0].value

@peer.handler("/test/out/ping", validator=PingResponse) #(1)!
def ping_handler(message: PingResponse):
    print(f"Received a ping message with response: {message.message}")
```

1. The `peer.handler` decorator is used to register the `ping_handler` function as a handler for messages sent to the `/test/out/ping` address, with the `PingResponse` model as its validator. Whenever a message with this address is received, it will first be validated against the `PingResponse` model, and if it passes validation, the `ping_handler` function will be called with the validated message as its argument.

##### Modifying Decorated Handlers {#modifying-decorated-handlers}

Handlers created with the `peer.handler` decorator can be modified after they have been created. The easiest way to do that is by using the fucntions associated with the handler object that is created by the decorator. These are exposed through the function that is decorated. Using the decorator is preffered for static handlers, and easier to understand if you are used to things like Flask or FastAPI.

```python
@peer.handler("/test/out/ping") #(1)!
def ping_handler(message):
    print(f"Received a ping message with args: {message.args}")

ping_handler.pause() #(2)!

ping_handler.unpause() #(3)!

ping_handler.unregister() #(4)!

```

1. The `peer.handler` decorator is used to register the `ping_handler` function as a handler for messages sent to the `/test/out/ping` address.
2. The `pause` method is called on the `ping_handler` function, which will temporarily disable the handler, preventing it from being called when a message with the `/test/out/ping` address is received.
3. The `unpause` method is called on the `ping_handler` function, which will re-enable the handler.
4. The `unregister` method is called on the `ping_handler` function, which will permanently remove the handler from the dispatcher, preventing it from being called when a message with the `/test/out/ping` address is received.



### `peer.register_handler` Method {#peer-register-handler-method}

The other way to create a handler is by using the `peer.register_handler` method. This allows you to register a handler in a way that is more conjucive to dynamic handler creation, as you can create and destroy handlers at any time. This method also allows you to specify an optional validator for the handler.

```python

def ping_handler(message):
    print(f"Received a ping message with args: {message.args}") #(1)!

peer.register_handler("/test/out/ping", ping_handler) #(2)!

```

1. The `ping_handler` function is defined to accept a message as its argument and print the arguments of the message.
2. The `register_handler` method is called on the `peer` object to register the `ping_handler` function as a handler for messages sent to the `/test/out/ping` address

##### Using Validators with `peer.register_handler`

The `peer.register_handler` method, like the decorator, also supports validators to ensure that the incoming data is validated, and can be easily accessed programatically within the handler.

```python
from pydantic import BaseModel

class PingResponse(BaseModel):
    args: tuple[OSCString]

    @property
    def message(self) -> str:
        return self.args[0].value #(1)!

def ping_handler(message: PingResponse):
    print(f"Received a ping message with response: {message.message}") #(2)!

peer.register_handler("/test/out/ping", ping_handler, validator=PingResponse) #(3)!

```

1. We define a `PingResponse` model that specifies the expected structure of the incoming message.
2. The `ping_handler` function is defined to accept a `PingResponse` object,
3. The `register_handler` method is called on the `peer` object to register the `ping_handler` function as a handler for messages sent to the `/test/out/ping` address, with the `PingResponse` model as its validator.

##### Modifying Registered Handlers {#modifying-registered-handlers}
Editing handlers that are created with the `peer.register_handler` method is a little bit more complicated. The easiest way to do it is by accessing the `Handler` object that is created by the method. Conveniently, the `register_handler` method returns the `Handler` object that is created, so you can easily store it in a variable and use that variable to modify the handler.

```python
def ping_handler(message):
    print(f"Received a ping message with args: {message.args}") #(1)!

handler = peer.register_handler("/test/out/ping", ping_handler) #(2)!


handler.pause() #(3)!

handler.unpause() #(4)!

handler.unregister() #(5)!

```

1. The `ping_handler` function is defined to accept a message as its argument and print the arguments of the message.
2. The `register_handler` method is called on the `peer` object to register the `ping_handler` function as a handler for messages sent to the `/test/out/ping` address. The `Handler` object that is created by the method is stored in the `handler` variable.
3. The `pause` method is called on the `handler` object, which will temporarily disable the handler, preventing it from being called when a message with the `/test/out/ping` address is received.
4. The `unpause` method is called on the `handler` object, which will re-enable the handler.
5. The `unregister` method is called on the `handler` object, which will permanently remove the handler from the dispatcher, preventing it from being called when a message with the `/test/out/ping` address is received.
   

## Validators {#validators}

When registering handlers, you can also provide an optional `validator`. A validator is a pydantic model that is used to validate incoming messages before they are passed to the handler. If the message does not conform to the validator, it will be rejected and not processed by the handler.

Here's an example of registering a handler with a validator:



```python
from pydantic import BaseModel #(1)!

class PingResponse(BaseModel): #(2)!
    args: tuple[OSCString]

    @property
    def message(self) -> str:
        return self.args[0].value #(3)!

@peer.handler("/test/out/ping", validator=PingResponse) #(4)!
def ping_handler(message: PingResponse):
    print(f"Received a ping message with response: {message.message}")

```

1. We import `BaseModel` from the `pydantic` library to create a validator model.
2. We define a `PingResponse` model that specifies the expected structure of the incoming message
3. We define a property `message` that extracts the string value from the first argument of the message.
4. The `ping_handler` function is defined to accept a `PingResponse` object, which will be validated before being passed to the handler. We use the decorator to register the handler for the `/test/out/ping` address, and specify the `PingResponse` model as its validator.


## Examples

Here is a complete example that demonstrates the use of a dispatcher with both a default handler and an address-specific handler with a validator:

##### Using the `@peer.handler` decorator with a validator


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


@peer.handler('/test/out/ping', validator=PingResponse) #(4)!
def ping_handler(message: PingResponse):
    print(f"Received a ping message with response: {message.message}") #(5)!

peer.start_listening() #(6)!
```

1. We create a `Peer` object that listens on localhost at port 3032 using TCP and OSC 1.1 framing.
2. We define a `PingResponse` model that specifies the expected structure of the incoming message
3. We define a property `message` that extracts the string value from the first argument of the message.    
4. We use the `peer.handler` decorator to register the handler for the `/test/out/ping` address, and specify the `PingResponse` model as its validator
5. The `ping_handler` function is defined to accept a `PingResponse` object, which will be validated before being passed to the handler. The function prints the message extracted from the `PingResponse` object.
6. We call the `start_listening` method on the `peer` object to start listening for incoming OSC messages.

##### Using the `register_handler` method with a validator


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

def ping_handler(message: PingResponse):
    print(f"Received a ping message with response: {message.message}") #(5)!

handler = peer.register_handler('/test/out/ping', ping_handler, validator=PingResponse) #(4)!

peer.start_listening() #(6)!
```

1. We create a `Peer` object that listens on localhost at port 3032 using TCP and OSC 1.1 framing.
2. We define a `PingResponse` model that specifies the expected structure of the incoming message
3. We define a property `message` that extracts the string value from the first argument of the message.    
4. We use the `peer.handler` decorator to register the handler for the `/test/out/ping` address, and specify the `PingResponse` model as its validator
5. The `ping_handler` function is defined to accept a `PingResponse` object, which will be validated before being passed to the handler. The function prints the message extracted from the `PingResponse` object.
6. We call the `start_listening` method on the `peer` object to start listening for incoming OSC messages.