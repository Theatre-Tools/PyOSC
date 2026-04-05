# Roadmap

## Version 1.1.0 (Latest Release)
The initial release covers the core functionality needed for OSC communication in Python.

**What's included:**

- Basic OSC message handling and dispatch
- TCP/UDP network communication via Peer
- CallHandler for request-response patterns
- Cross-platform support (Windows, macOS, Linux)
- Error handling and logging
- API documentation and tutorials
- Unit tests for critical components
- Time-tagged message scheduling

Version 1.1.0 will bring a varity of feature updates, including:

  - Implemented TCP connection flags for increased speed and lower latency
  - Enhanced event and error handling using decorators for cleaner code and easier debugging
  - Added Deprecation warning to ```add_handler('/*')``` to warn users of it's deprecation in it's current form. This is due to an oversight in the original dispatcher that ignored address lengths when dispatching messages. This will be fixed in 2.0.0 and we will then be more closely aligned with the OSC Specification.

If you are interested in testing the current release candidate for 1.1.0, it can be installed using the following commands:

=== "Pip"

    ```bash
    pip install pyopensoundcontrol=1.1.0rc4
    ```
=== "Poetry"

    ```bash
    poetry add pyopensoundcontrol=1.1.0rc4
    ```

## Upcoming Features (May include breaking changes)

### 2.0.0
Version 2.0.0 will be a major release that includes breaking changes to align more closely with the OSC specification and to improve the overall design of the library. Some of the planned changes include:

- Implement proper address pattern matching in the dispatcher, including matching the address length
- Rework the method by which handlers are registered. Moving away from the current method of registering handlers individually to registering them at definition, by using decorators. This will reduce clutter and make it easier to pick up the library, especially for users who are used to HTTP frameworks like fastapi and flask. This was trialled in the event handlers coming to version 1.1.0
- Refactor the Call Handler to make it a bit more streamlined.

There is also space in this release to add more features, as it is likely a month off release candiadates, so if there is anything you would like implemented, please create an issue or submit a pull request with your proposed changes.





## Future

These are things I'd like to have implemented at some point, but haven't yet been prioritized for a planned release.

**Dispatcher enhancements**

- Add support for exclusions in dispatch handlers, so we don't need hacky solutions with subsequent handlers that do nothing.

**Improved Error Handling**
- Implement more robust error handling and logging throughout the library, especially in network communication and message parsing.
- Provide clearer errors on validation failures to make it easier to diagnose issues with message formats and

## Future

**Subscription system**

- Implement pub/sub patterns for OSC messages
- Allow clients to subscribe to specific address patterns

**Other potential features**

- Bundle support for batched messages
- Connection pooling and multiplexing
- Better debugging and introspection tools

## Contributing
See [CONTRIBUTING.MD](./contributing.md) for how to propose features or submit improvements.