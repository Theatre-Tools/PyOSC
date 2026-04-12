## Define a type variable for the controller that is covariant, allowing it to accept subclasses of BaseModel
import re
from typing import Callable, ParamSpec, Protocol, TypeVar

from pydantic import BaseModel, ValidationError


class DispatcherInterface[T: BaseModel](Protocol):
    def __call__(self, message: T) -> None: ...


## Define custom exceptions for the dispatcher to provide more specific error handling capabilities.
class DispatcherValidationError(ValueError):
    pass


class DispatcherMissingFieldError(DispatcherValidationError):
    pass


class DispatcherTypeMismatchError(DispatcherValidationError):
    pass


T_C = TypeVar("T_C", bound=BaseModel, covariant=True)

## Define a ParamSpec for the handler function parameters
P = ParamSpec("P")
R_co = TypeVar("R_co", covariant=True)


# Define a protocol for the decorated handler that includes the additional methods for unregistering, pausing, and unpausing.
# This allows the decorated function to be used as a normal callable while also providing the extra functionality needed for handler management.
class DecoratedHandler(Protocol[P, R_co]):
    def __call__(self, *args: P.args, **kwargs: P.kwargs) -> R_co: ...

    def unregister(self) -> None: ...

    def pause(self) -> None: ...

    def unpause(self) -> None: ...


class Handler:
    """Handler object contains an address pattern, a dispatcher, and any other methods attached to handlers.
    Makes it easier to create, destroy and edit handlers after creation.
    Replaced previous implementation where handlers were stored as a Dispatch Controller and a Dispatch Matcher wrapped in a tuple.
    """

    def __init__(
        self,
        dispatcher: DispatcherInterface[T_C],
        validator: type[T_C],
        pattern: re.Pattern,
        enabled: bool = True,
    ):
        self.pattern = pattern
        self.enabled = enabled
        self._unregister_action: Callable
        self._pause_action: Callable
        self._unpause_action: Callable
        self.dispatcher = dispatcher
        self.validator = validator

    def matches(self, address: str) -> bool:
        """This method checks if the given OSC address matches the handler's address pattern using the compiled regular expression.

        Args:
            address (str): The OSC address to check.

        Returns:
            bool: True if the address matches the handler's pattern, False otherwise.
        """
        return self.pattern.fullmatch(address) is not None

    def __hash__(self) -> int:
        """Hash based on the handler's address pattern, allowing handlers to be used in sets and as dictionary keys.

        Returns:
            int: The hash value of the handler.
        """
        return hash(self.pattern)

    def run(self, message: BaseModel):
        """This method validates the incoming message using the handler's pydantic validator and then calls the dispatcher function with the validated message.
         It also includes detailed error handling to provide specific feedback on validation issues.

        Args:
            message (BaseModel): The message to validate and dispatch.

        Raises:
            DispatcherMissingFieldError: Raised when required fields are missing from the message.
            DispatcherTypeMismatchError: Raised when there is a type mismatch in the message.
            DispatcherValidationError: Raised when the message fails validation for other reasons.
            Exception: Raised for any other unexpected errors.
        """
        try:
            validated_message = self.validator.model_validate(message.model_dump())
            self.dispatcher(validated_message)
        except ValidationError as e:
            errors = e.errors()
            formatted_errors = "; ".join(f"{error['loc']}: {error['msg']} ({error['type']})" for error in errors)
            if any(error["type"] == "missing" for error in errors):
                raise DispatcherMissingFieldError(
                    f"Validation error: Missing required fields in message {message}. {formatted_errors}"
                )
            if any(error["type"].endswith("_type") for error in errors):
                raise DispatcherTypeMismatchError(f"Validation error: Type mismatch in message {message}. {formatted_errors}")
            raise DispatcherValidationError(f"Validation error: Invalid message {message}. {formatted_errors}")
        except Exception as e:
            raise Exception(f"Error in handler: {e}")

    def bind_controls(
        self,
        unregister_action: Callable[[], None],
        pause_action: Callable[[], None],
        unpause_action: Callable[[], None],
    ) -> None:
        self._unregister_action = unregister_action
        self._pause_action = pause_action
        self._unpause_action = unpause_action

    @classmethod
    def pattern_generator(cls, address: str) -> re.Pattern:
        reg_pattern = ""
        i = 0

        while i < len(address):
            char = address[i]

            if char == "?":
                # ? matches any single character
                reg_pattern += "."
                i += 1
            elif char == "*":
                # * matches zero or more characters within one address segment
                reg_pattern += "[^/]*"
                i += 1
            elif char == "[":
                # Square brackets - character class
                j = i + 1
                # Check if it starts with !
                if j < len(address) and address[j] == "!":
                    # Negated character class
                    reg_pattern += "[^"
                    j += 1
                else:
                    reg_pattern += "["

                # Copy contents until closing bracket
                while j < len(address) and address[j] != "]":
                    reg_pattern += address[j]
                    j += 1

                if j < len(address):
                    reg_pattern += "]"
                    i = j + 1
                else:
                    # No closing bracket found, treat as literal
                    reg_pattern += re.escape("[")
                    i += 1
            elif char == "{":
                # Curly braces - comma-separated alternatives
                j = i + 1
                alternatives = []
                current = ""

                while j < len(address) and address[j] != "}":
                    if address[j] == ",":
                        alternatives.append(current)
                        current = ""
                    else:
                        current += address[j]
                    j += 1

                if j < len(address):
                    alternatives.append(current)
                    # Escape each alternative
                    escaped_alternatives = [re.escape(alt) for alt in alternatives]
                    reg_pattern += "(" + "|".join(escaped_alternatives) + ")"
                    i = j + 1
                else:
                    # No closing brace found, treat as literal
                    reg_pattern += re.escape("{")
                    i += 1
            else:
                # Regular character - escape it if it has special meaning in regex
                reg_pattern += re.escape(char)
                i += 1

        return re.compile(reg_pattern)

    @classmethod
    def from_address(
        cls,
        address: str,
        func: Callable,
        validator: type[BaseModel],
    ) -> "Handler":
        """Method by whiuch Handlers are normally created, as it handles the creation of the DispatchMatcher and DispatchController based on the provided address, function and validator.

        Args:
            address (str): The OSC address pattern to match for this handler.
            func (Callable): The function to call when a message matching the address is received.
            validator (type[BaseModel]): The pydantic validator to use for validating incoming messages.
            enabled (Optional[bool], optional): Whether the handler is enabled. Defaults to True.

        Returns:
            Handler: The created handler.
        """

        return cls(
            dispatcher=func,
            validator=validator,
            pattern=cls.pattern_generator(address),
            enabled=True,
        )

    def unregister(self) -> None:
        """Proxy method for unregister

        Raises:
            ValueError: If the unregister action is not bound to this handler, which should never happen if handlers are created through the Dispatcher's register_handler method or handler decorator.
        """
        if not self._unregister_action:
            raise ValueError("Unregister action not bound for this handler.")
        self._unregister_action()

    def pause(self) -> None:
        """Proxy method for pause

        Raises:
            ValueError: If the pause action is not bound to this handler, which should never happen if handlers are created through the Dispatcher's register_handler method or handler decorator.
        """
        if not self._pause_action:
            raise ValueError("Pause action not bound for this handler.")
        self._pause_action()

    def unpause(self) -> None:
        """Proxy method for unpause

        Raises:
            ValueError: If the unpause action is not bound t othis handler, which should never happen if handlers are created through the Dispatcher's register_handler method or handler decorator.
        """
        if not self._unpause_action:
            raise ValueError("Unpause action not bound for this handler.")
        self._unpause_action()
