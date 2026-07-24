class PeerNotConnectedError(Exception):
    """Raised when attempting to send a message to a peer that is not connected."""

    pass


class DispatcherMissingFieldError(ValueError):
    """Raised when required fields are missing from the message."""

    pass


class DispatcherTypeMismatchError(ValueError):
    """Raised when there is a type mismatch in the message."""

    pass


class DispatcherValidationError(ValueError):
    """Raised when the message fails validation for other reasons."""

    pass


class HandlerRegistrationError(Exception):
    """Raised when there is an error during handler registration."""

    pass


class SocketError(Exception):
    """Raised when there is a socket error."""

    pass


class PeerInitializationError(Exception):
    """Raised when there is an error during peer initialization."""

    pass


class PeerError(Exception):
    """Base exception for peer-related errors."""


class PeerConfigurationError(PeerError):
    """Raised when a peer is configured with invalid arguments."""


class PeerConnectionError(PeerError):
    """Raised when a peer cannot establish or use its transport connection."""


class PeerListenerError(PeerError):
    """Raised when a background listener fails."""


class CallHandlerValidationError(ValueError):
    """Raised when a message fails validation in the call handler."""
