# Roadmap

## Version 1.0 (Current)
The initial release covers the core functionality needed for OSC communication in Python.

**What's included:**

- Basic OSC message handling and dispatch
- TCP/UDP network communication via Peer
- CallHandler for request-response patterns
- Cross-platform support (Windows, macOS, Linux)
- Error handling and logging
- API documentation and tutorials
- Unit tests for critical components

## Upcomoing Features (May include breaking changes)

**Handler improvements**

- Streamline CallHandler so it's created as the default handler when Peer is initialized. This will reduce boilerplate but may require some refactoring of the Peer object.
- Replace the current default handler with a default CallHandler that can be customized or overwritten.

**Dispatcher enhancements**

- Add support for exclusions in dispatch handlers, so we don't need hacky solutions with subsequent handlers that do nothing.

## Future

**Subscription system**

- Implement pub/sub patterns for OSC messages
- Allow clients to subscribe to specific address patterns

**Other potential features**

- Bundle support for batched messages
- Time-tagged message scheduling
- Connection pooling and multiplexing
- Better debugging and introspection tools

## Contributing
See [CONTRIBUTING.MD](./contributing.md) for how to propose features or submit improvements.