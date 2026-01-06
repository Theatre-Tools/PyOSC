# Sending an OSC Message

Here I'll explain how to send a simple OSC message, aswell as breaking down the code to explain how it works.


In this example I will assume you have already initialized a [`Peer`](../api_reference.md#peer){ data-preview } object called `peer`, if you need help with this please refer to the [Peer Object Tutorial](./peer.md){ data-preview }.
```python
message = OSCMessage(
    address="/test/message", #(1)!
    args=(
        OSCInt(value=42), #(2)!
        OSCString(value="Hello_World!") #(3)!
    )
)

peer.send_message(message) #(4)!
```

1. The `address` parameter specifies the OSC address pattern for the message. In this case, the message is being sent to the address `/test/message`.
2. The first argument in the `args` tuple is an `OSCInt` object with a value of `42`. This represents a 32-bit integer argument in the OSC message.
3. The second argument in the `args` tuple is an `OSCString` object with a value of `Hello_World!`. This represents a string argument in the OSC message.
4. The [`send_message`](../api_reference.md#peer#send_message){ data-preview } method of the [`Peer`](../api_reference.md#peer){ data-preview } object is called with the constructed [`OSCMessage`](../api_reference.md#oscmessage){ data-preview } object as an argument. This sends the OSC message to the specified address with the provided arguments.

Here is the example from before, where we send a simple messsage, with two arguments. The arguments are an integer with the value `42`, and a string with the value `Hello_World!`.

Below is a list of possible argument types that are compatible with OSC messages in PyOSC:

- `OSCInt` - Represents a 32-bit integer.
- `OSCFloat` - Represents a 32-bit floating-point number.
- `OSCString` - Represents a string.
- `OSCInt64` - Represents a 64-bit integer.
- `OSCTimeTag` - Represents an OSC Time Tag.
- `OSCDouble` - Represents a 64-bit floating-point number.
- `OSCBlob` - Represents a binary large object (blob).
- `OSCChar` - Represents a single character.
- `OSCSymbol` - Represents an OSC symbol.
- `OSCNil` - Represents a nil value.
- `OSCRGBA` - Represents an RGBA color value.
- `OSCMidi` - Represents a MIDI message.
- `OSCImpulse` - Represents an impulse value.
- `OSCArray` - Represents an array of OSC arguments.
- Boolean values are represented using `OSCFalse` and `OSCTrue`.