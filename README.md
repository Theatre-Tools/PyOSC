# PyOSC

Python library to support OSC (Open Sound Control).

## About the Project

I had issues getting the support I needed out of any of the other packages, so I decide how hard can it be...

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

## License
This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details. 