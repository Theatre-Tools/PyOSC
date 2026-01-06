# The Dispatcher

The [`Dispatcher`](../api_reference.md#dispatcher){ data-preview } object in PyOSC is what routes incoming OSC messages based on their address. It's implementation is simple and efficient, allowing you to easily register handler based on methods, addresses and pydanntic models.

## Creating a Dispatcher
Dispatchers no longer need to be explicitly created, as they are now automatically initialized when you create a [`Peer`](../api_reference.md#peer){ data-preview } object. However, if you need to create one manually, you can do so like this:

```python
from pyosc import Dispatcher

dispatcher = Dispatcher()
```

## Registering Handlers

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