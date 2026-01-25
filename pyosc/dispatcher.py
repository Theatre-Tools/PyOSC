from threading import Lock
from typing import Generic, Protocol, TypeVar, overload
import re
from oscparser import OSCMessage
from pydantic import BaseModel, ValidationError


class DispatcherInterface[T: BaseModel](Protocol):
    def __call__(self, message: T) -> None: ...


T_C = TypeVar("T_C", bound=BaseModel, covariant=True)


class DispatcherController(Generic[T_C]):
    def __init__(
        self, dispatcher: "DispatcherInterface[T_C]", validator: type[T_C]
    ) -> None:
        self.dispatcher = dispatcher
        self.validator = validator

    def run(self, message: BaseModel):
        try:
            validated_message = self.validator.model_validate(message.model_dump())
            self.dispatcher(validated_message)
        except ValidationError:
            pass


class DispatchMatcher:
    def __init__(self, pattern: re.Pattern) -> None:
        self.pattern = pattern

    @classmethod
    def from_address(cls, address: str) -> 'DispatchMatcher':
        reg_pattern = ''
        i = 0
        
        while i < len(address):
            char = address[i]
            
            if char == '?':
                # ? matches any single character
                reg_pattern += '.'
                i += 1
            elif char == '*':
                # * matches any sequence of zero or more characters
                reg_pattern += '.*'
                i += 1
            elif char == '[':
                # Square brackets - character class
                j = i + 1
                # Check if it starts with !
                if j < len(address) and address[j] == '!':
                    # Negated character class
                    reg_pattern += '[^'
                    j += 1
                else:
                    reg_pattern += '['
                
                # Copy contents until closing bracket
                while j < len(address) and address[j] != ']':
                    reg_pattern += address[j]
                    j += 1
                
                if j < len(address):
                    reg_pattern += ']'
                    i = j + 1
                else:
                    # No closing bracket found, treat as literal
                    reg_pattern += re.escape('[')
                    i += 1
            elif char == '{':
                # Curly braces - comma-separated alternatives
                j = i + 1
                alternatives = []
                current = ''
                
                while j < len(address) and address[j] != '}':
                    if address[j] == ',':
                        alternatives.append(current)
                        current = ''
                    else:
                        current += address[j]
                    j += 1
                
                if j < len(address):
                    alternatives.append(current)
                    # Escape each alternative
                    escaped_alternatives = [re.escape(alt) for alt in alternatives]
                    reg_pattern += '(' + '|'.join(escaped_alternatives) + ')'
                    i = j + 1
                else:
                    # No closing brace found, treat as literal
                    reg_pattern += re.escape('{')
                    i += 1
            else:
                # Regular character - escape it if it has special meaning in regex
                reg_pattern += re.escape(char)
                i += 1

        return cls(re.compile(reg_pattern))

    def matches(self, address: str) -> bool:
        return self.pattern.fullmatch(address) is not None

    def __hash__(self) -> int:
        return hash(self.pattern)


class Dispatcher:
    """Dispatches incoming OSC messages to registered handlers based on their addresses."""

    def __init__(self):
        self.handlers: list[tuple[DispatchMatcher, DispatcherController[BaseModel]]] = (
            []
        )
        self.dispatch_cache: dict[str, tuple[DispatcherController[BaseModel], ...]] = {}
        self.dispatch_lock: Lock = Lock()

    @overload
    def add_handler(
        self, address: str, handler: DispatcherInterface[OSCMessage]
    ) -> None: ...

    @overload
    def add_handler[T: BaseModel](
        self, address: str, handler: DispatcherInterface[T], validator: type[T]
    ) -> None: ...

    def add_handler[T: BaseModel](
        self,
        address: str,
        handler: DispatcherInterface[T],
        validator: type[T] = OSCMessage,
    ):
        """
        Add a handler for a specific OSC address.
        - ``address``: The OSC address to handle.
        - ``handler``: A callable that takes an OSCMessage as its only argument.
        """
        matcher = DispatchMatcher.from_address(address)
        self.handlers.append((matcher, DispatcherController(handler, validator)))


    def remove_handler(self, address: str):
        """
        Removes a handler for a specific OSC address.
        - ``address``: The OSC address to remove the handler for.
        """
        removed_handlers: list[
            tuple[DispatchMatcher, DispatcherController[BaseModel]]
        ] = []
        with self.dispatch_lock:
            for item in self.handlers:
                matcher, _ = item
                if matcher.pattern == address:
                    removed_handlers.append(item)
                    return

            for handler in removed_handlers:
                self.handlers.remove(handler)

            self.dispatch_cache = {}

    def dispatch(self, message: OSCMessage):
        """
        Dispatches an incoming OSC message to the appropriate handler based on its address.
        - ``message``: The incoming OSCMessage to dispatch.
        """

        with self.dispatch_lock:
            if message.address in self.dispatch_cache:
                for handler in self.dispatch_cache[message.address]:
                    handler.run(message)
                return

        matched_handlers: list[DispatcherController[BaseModel]] = []
        with self.dispatch_lock:
            for matcher, handler in self.handlers:
                if matcher.matches(message.address):
                    matched_handlers.append(handler)
            self.dispatch_cache[message.address] = tuple(matched_handlers)

        for handler in matched_handlers:
            handler.run(message)
