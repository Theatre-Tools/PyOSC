# The roadmap

## Upcoming Features
- Subscription support
- Streamline the CallHandler, so that it is created as the default handler when Peer is initialized (May need a bit of refractoring of the Peer object)
- Add support for exclusions in dispatch handlers (as apposed to doing hacky solutions with subsequesnt handlers that do nothing.)
- Depricate the default handler in it's current form, to be replaced with a default CallHandler that can be customized or overwritten.
  

## Version 1.0
- Initial release with core features
- Reasonable error handling and logging
- Basic documentation
- Unit tests for critical components
- Support for major platforms (Windows, macOS, Linux)
  