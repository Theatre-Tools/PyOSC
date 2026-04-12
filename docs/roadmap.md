# Roadmap

## Version 2.0.0b1 (Latest Pre-release build (April 2026))

**What's included:**

  - Basic OSC message handling and dispatch
  - TCP/UDP network communication via Peer
  - CallHandler for request-response patterns
  - Cross-platform support (Windows, macOS, Linux)
  - Error handling and logging
  - API documentation and tutorials
  - Unit tests for critical components
  - Time-tagged message scheduling
  - Implemented TCP connection flags for increased speed and lower latency
  - Enhanced event and error handling using decorators for cleaner code and easier debugging
  - Added Deprecation warning to ```add_handler('/*')``` to warn users of it's deprecation in it's current form. This is due to an oversight in the original dispatcher that ignored address lengths when dispatching messages. This will be fixed in 2.0.0 and we will then be more closely aligned with the OSC Specification.


### 2.0.0 (Planned for Late April 2026)

Below are the things that have currently been implemented in 2.0.0, and are shipped in the public beta (b1), but are still being actively worked on.

- Implement proper address pattern matching in the dispatcher, including matching the address length
- Rework the method by which handlers are registered. Moving away from the current method of registering handlers individually to registering them at definition, by using decorators. This will reduce clutter and make it easier to pick up the library, especially for users who are used to HTTP frameworks like fastapi and flask. This was trialled in the event handlers coming to version 1.1.0
- Refactor the Call Handler to make it a bit more streamlined.

There is also space in this release to add more features, as it is likely a month off release candiadates, so if there is anything you would like implemented, please create an issue or submit a pull request with your proposed changes.

You can install the latest pre-release build with pip:

=== "Pip"

    ```bash
    pip install "pyopensoundcontrol>=2.0.0b10"
    ```
=== "Poetry"

    ```bash
    poetry add "pyopensoundcontrol>=2.0.0b10"
    ```





## Future

These are things I'd like to have implemented at some point, but haven't yet been prioritized for a planned release.

**Improved Error Handling**
- Implement more robust error handling and logging throughout the library, especially in network communication and message parsing.
- Provide clearer errors on validation failures to make it easier to diagnose issues with message formats and


**Other potential features**

- Bundle support for batched messages
- Connection pooling and multiplexing
- Better debugging and introspection tools

## Contributing
See [CONTRIBUTING.MD](./contributing.md) for how to propose features or submit improvements.