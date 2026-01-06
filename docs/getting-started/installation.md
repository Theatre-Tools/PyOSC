# Introduction to PyOSC

This is the documentation for PyOSC, a library for Pytthon to handle the transport of OSC messages and Bundles over a network. It depends on [`oscparser`](https://github.com/Theatre-Tools/python-osc-parser) to parse and serialize OSC messages.

## Prerequisites

PyOSC requires Python 3.14 or greater, earlier versions of Python are not supported and will not work.

## Installation
PyOSC is available on PyPI, so installation is simple using the following commands:
=== "Pip"

    ```bash
    pip install pyosc
    ```
=== "Poetry"

    ```bash
    poetry add pyosc
    ```

## Basic Usage

Here is a quick example as to how to send a simple OSC message using PyOSC:

```python
from pyosc import Peer, OSCMessage, OSCModes, OSCFraming, Dispatcher, OSCInt, OSCString

peer = Peer(
    "127.0.0.1",
    3032,
    mode=OSCModes.TCP,
    framing=OSCFraming.OSC11,
)
message = OSCMessage(
    address="/test/message",
    args=(
        OSCInt(value=42),
        OSCString(value="Hello"),
    )
)
peer.send_message(message)
```
For more detailed examples and advanced usage, please refer to the subsequent sections of this documentation.