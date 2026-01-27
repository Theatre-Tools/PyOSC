import heapq
import re
import time
from threading import Event, RLock, Thread
from typing import Generic, Protocol, TypeVar, overload

from oscparser import OSCBundle, OSCMessage
from pydantic import BaseModel, ValidationError


class DispatcherInterface[T: BaseModel](Protocol):
    def __call__(self, message: T) -> None: ...


T_C = TypeVar("T_C", bound=BaseModel, covariant=True)


class DispatcherController(Generic[T_C]):
    def __init__(self, dispatcher: "DispatcherInterface[T_C]", validator: type[T_C]) -> None:
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
    def from_address(cls, address: str) -> "DispatchMatcher":
        reg_pattern = ""
        i = 0

        while i < len(address):
            char = address[i]

            if char == "?":
                # ? matches any single character
                reg_pattern += "."
                i += 1
            elif char == "*":
                # * matches any sequence of zero or more characters
                reg_pattern += ".*"
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

        return cls(re.compile(reg_pattern))

    def matches(self, address: str) -> bool:
        return self.pattern.fullmatch(address) is not None

    def __hash__(self) -> int:
        return hash(self.pattern)


class Dispatcher:
    """Dispatches incoming OSC messages to registered handlers based on their addresses."""

    def __init__(self):
        self.handlers: list[tuple[DispatchMatcher, DispatcherController[BaseModel]]] = []
        self.dispatch_cache: dict[str, tuple[DispatcherController[BaseModel], ...]] = {}
        self.dispatch_lock: RLock = RLock()
        self._scheduled_heap: list[tuple[float, int, OSCBundle]] = []
        self._scheduler_lock: RLock = RLock()
        self._scheduler_counter = 0
        self._stop_scheduler = Event()
        self._scheduler_thread: Thread | None = None

    @overload
    def add_handler(self, address: str, handler: DispatcherInterface[OSCMessage]) -> None: ...

    @overload
    def add_handler[T: BaseModel](self, address: str, handler: DispatcherInterface[T], validator: type[T]) -> None: ...

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

    def start_scheduler(self):
        """Start the background thread for processing timestamped bundles."""
        if self._scheduler_thread is None or not self._scheduler_thread.is_alive():
            self._stop_scheduler.clear()
            self._scheduler_thread = Thread(target=self._scheduler_worker, daemon=True)
            self._scheduler_thread.start()

    def stop_scheduler(self):
        """Stop the background scheduler thread."""
        self._stop_scheduler.set()
        if self._scheduler_thread and self._scheduler_thread.is_alive():
            self._scheduler_thread.join(timeout=1)

    def _scheduler_worker(self):
        """Background worker that processes scheduled bundles at their timetags."""
        while not self._stop_scheduler.is_set():
            with self._scheduler_lock:
                if self._scheduled_heap:
                    scheduled_time, _, bundle = self._scheduled_heap[0]
                    current_time = time.time()
                    if current_time >= scheduled_time:
                        heapq.heappop(self._scheduled_heap)
                        # Process bundle outside the lock
                        self._process_bundle_immediate(bundle)
                        continue
            time.sleep(0.001)  # Small sleep to prevent busy waiting

    def remove_handler(self, address: str):
        """
        Removes a handler for a specific OSC address.
        - ``address``: The OSC address to remove the handler for.
        """
        removed_handlers: list[tuple[DispatchMatcher, DispatcherController[BaseModel]]] = []
        with self.dispatch_lock:
            for item in self.handlers:
                matcher, _ = item
                if matcher.pattern == address:
                    removed_handlers.append(item)
                    return

            for handler in removed_handlers:
                self.handlers.remove(handler)

            self.dispatch_cache = {}

    def dispatch(self, message: OSCMessage | OSCBundle):
        """
        Dispatches an incoming OSC message to the appropriate handler based on its address.
        - ``message``: The incoming OSCMessage or OSCBundle to dispatch.
        """
        if not isinstance(message, OSCMessage):
            self.dispatch_bundle(message)
            return

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

    def dispatch_bundle(self, bundle: OSCBundle):
        """
        Dispatches an OSC bundle. If the bundle has a timetag in the future,
        it is scheduled for later execution. Otherwise, it's processed immediately.
        Nested bundles are supported and processed recursively.
        - ``bundle``: The OSCBundle containing messages and/or nested bundles to dispatch.
        """
        # timetag is a 64-bit NTP timestamp (int)
        # 0 means "immediately"
        if bundle.timetag == 0:
            # Immediate execution
            self._process_bundle_immediate(bundle)
        else:
            # Convert NTP timestamp to Unix timestamp
            # NTP epoch is 1900-01-01, Unix epoch is 1970-01-01
            # Difference is 2208988800 seconds
            OSC_EPOCH_OFFSET = 2208988800

            # Split 64-bit NTP timestamp into seconds and fractional seconds
            ntp_seconds = bundle.timetag >> 32
            ntp_fraction = bundle.timetag & 0xFFFFFFFF

            # Convert to Unix timestamp
            bundle_time = (ntp_seconds - OSC_EPOCH_OFFSET) + (ntp_fraction / (2**32))
            current_time = time.time()

            if bundle_time <= current_time:
                # Time has passed or is now, process immediately
                self._process_bundle_immediate(bundle)
            else:
                # Schedule for future execution
                with self._scheduler_lock:
                    self._scheduler_counter += 1
                    heapq.heappush(
                        self._scheduled_heap,
                        (bundle_time, self._scheduler_counter, bundle),
                    )
                # Ensure scheduler is running
                self.start_scheduler()

    def _process_bundle_immediate(self, bundle: OSCBundle):
        """
        Process bundle contents immediately and atomically.
        Handles both messages and nested bundles recursively.
        """
        with self.dispatch_lock:
            for item in bundle.elements:
                if isinstance(item, OSCMessage):
                    # Look up or build handler list for this address
                    if item.address in self.dispatch_cache:
                        handlers = self.dispatch_cache[item.address]
                    else:
                        matched_handlers: list[DispatcherController[BaseModel]] = []
                        for matcher, handler in self.handlers:
                            if matcher.matches(item.address):
                                matched_handlers.append(handler)
                        handlers = tuple(matched_handlers)
                        self.dispatch_cache[item.address] = handlers

                    # Execute all handlers for this message
                    for handler in handlers:
                        handler.run(item)
                elif isinstance(item, OSCBundle):
                    # Nested bundle - process recursively
                    # RLock allows the same thread to acquire the lock again
                    self._process_bundle_immediate(item)
