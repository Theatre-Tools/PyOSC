# PyOSC

Python library to support OSC (Open Sound Control).

## About the Project

I had issues getting the support I needed out of any of the other packages, so I decided to build my own from scratch. I wanted something that was simple to use, and handled OSC peers in a way that makes sense to me, given that most libruaryies try and apply a client server model that doesn't really exist in OSC. I also wanted to support both UDP and TCP transport protocols, as well as both OSC version 1.0 and 1.1. I wanted to make sure the library was flexible enough for me to work the way I wanted to work, and that it would be easy to treat OSC more as an API, than as a messaging protocol.

## Features
- Support for both UDP and TCP transport protocols
- Flexible message handling with customizable handlers
- Support for both OSC version 1.0 and 1.1
- Background processing of incoming messages to avoid blocking the main thread
- Simple API for sending OSC messages to remote hosts

## Installation
You can install PyOSC using pip:

```bash
pip install pyopensoundcontrol
```
or when using poetry:

```bash
poetry add pyopensoundcontrol
```

## Documentation
The documentation is currently hosted [here](https://theatre-tools.github.io/PyOSC/latest/), with the source files located inside the `docs` directory in this repository should you want to contribute to it or run it locally.

## Bugs and Issues
If you encounter any bugs or issues, please report them on the [GitHub Issues page](https://github.com/theatre-tools/PyOSC/issues). Make sure to include a clear description of the problem, steps to reproduce it, and any relevant code snippets or error messages.

## Contributing
Contributions are welcome! If you would like to contribute to the project, please follow these steps:
1. Fork the repository and create a new branch for your feature or bug fix.
2. Make your changes and ensure that they are well-documented and tested.
3. Submit a pull request with a clear description of your changes and why they are needed.
4. The maintainers will review your pull request and provide feedback or merge it if it meets the project's standards.
5. Please read the [CONTRIBUTING.md](docs/contributing.md) file for more detailed guidelines on contributing to the project.

## Roadmap
See [ROADMAP.md](docs/roadmap.md) for the current roadmap and upcoming features

## Dependencies and Thank yous
- [oscparser](https://github.com/Theatre-Tools/python-osc-parser) - A pure Python OSC message parser that supports both OSC 1.0 and 1.1 formats. This library was written by a friend of mine specifically for this project to ensure we have a reliable and flexible OSC parsing solution that meets our needs.
- [pytest](https://docs.pytest.org/en/stable/) - A testing framework for Python that makes it easy to write simple and scalable test cases.
- [socket](https://docs.python.org/3/library/socket.html) - A built-in Python library for low-level network communication, used for sending and receiving OSC messages over UDP and TCP.
- [threading](https://docs.python.org/3/library/threading.html) - A built-in Python library for creating and managing threads, used to handle incoming OSC messages without blocking the main thread.
- [typing](https://docs.python.org/3/library/typing.html) - A built-in Python library that provides support for type hints, used to improve code readability and maintainability.
- [select](https://docs.python.org/3/library/select.html) - A built-in Python library that provides access to the select() function, used for monitoring multiple file descriptors (sockets) for events such as incoming data.
- [Material for MKDocs](https://squidfunk.github.io/mkdocs-material/) - A modern and responsive theme for MkDocs, used to create the documentation for this project.

## License
This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.