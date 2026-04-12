import heapq
import time
import warnings
from threading import Event, RLock, Thread
from typing import (
    Callable,
    cast,
    overload,
)

from oscparser import OSCBundle, OSCMessage
from pydantic import BaseModel

from .handler import DecoratedHandler, DispatcherInterface, Handler, P, R_co


class Dispatcher:
    """The Dispatcher Object contains all the information and logic necessary to route incoming OSC messages to the correct handler functions based on their addresses.
    It supports dynamic registration and deregistration of handlers, as well as scheduling of messages in bundles based on their timetags.
    """

    def __init__(
        self,
        error_emit: Callable,
    ):
        self.handlers: list[Handler] = []
        self.dispatch_cache: dict[str, tuple[Handler, ...]] = {}
        self.dispatch_lock: RLock = RLock()
        self._scheduled_heap: list[tuple[float, int, OSCBundle]] = []
        self._scheduler_lock: RLock = RLock()
        self._scheduler_counter = 0
        self._stop_scheduler = Event()
        self._scheduler_thread: Thread | None = None
        self.error_emit = error_emit

    @overload
    def add_handler(self, address: str, func: DispatcherInterface[OSCMessage]) -> Handler: ...

    @overload
    def add_handler[T: BaseModel](
        self, address: str, func: DispatcherInterface[OSCMessage], validator: type[T]
    ) -> Handler: ...

    def add_handler[T: BaseModel](
        self,
        address: str,
        func: DispatcherInterface[OSCMessage],
        validator: type[T] = OSCMessage,
    ) -> Handler:
        """Registers a Dispatch Handler for a specific OSC address pattern with an optional pydantic validator.

        Args:
            address (str): The OSC address pattern to match for this handler.
            func (DispatcherInterface[OSCMessage]): The function to call when a message matching the address is received.
            validator (type[BaseModel]): The pydantic validator to use for validating incoming messages.
        Returns:
            Handler: The registered handler.
        """
        warnings.warn(
            "add_handler is deprecated and will be removed in a future release. Please use the handler decorator or register_handler instead for cleaner and more intuitive handler definitions.",
            DeprecationWarning,
            stacklevel=2,
        )
        return self.register_handler(address, func, validator)

    @overload
    def register_handler(self, address: str, func: DispatcherInterface[OSCMessage]) -> Handler: ...

    @overload
    def register_handler[T: BaseModel](
        self, address: str, func: DispatcherInterface[OSCMessage], validator: type[T]
    ) -> Handler: ...

    def register_handler[T: BaseModel](
        self,
        address: str,
        func: DispatcherInterface[OSCMessage],
        validator: type[T] = OSCMessage,
    ) -> Handler:
        """Registers a Dispatch Handler for a specific OSC address pattern with an optional pydantic validator.

        Args:
            address (str): The OSC address pattern to match for this handler.
            func (DispatcherInterface[OSCMessage]): The function to call when a message matching the address is received.
            validator (type[BaseModel]): The pydantic validator to use for validating incoming messages.

        Returns:
            Handler: The registered handler.
        """
        try:
            handler = Handler.from_address(address, func, validator)
        except Exception as e:
            raise ValueError(f"Error registering handler for address pattern '{address}': {e}") from e

        def unregister() -> None:
            """Permanently unregisters the handler from the dispatcher."""
            with self.dispatch_lock:
                if handler in self.handlers:
                    self.handlers.remove(handler)
                    self.dispatch_cache = {}
                else:
                    warnings.warn(
                        "Handler not found in dispatcher, cannot unregister.",
                        stacklevel=2,
                    )

        def pause() -> None:
            """Temporaily disables a handler"""
            with self.dispatch_lock:
                handler.enabled = False
                self.dispatch_cache = {}

        def unpause() -> None:
            """Re-enables a previously disabled handler"""
            with self.dispatch_lock:
                handler.enabled = True
                self.dispatch_cache = {}

        # Bit of a hack to bind the control functions to the handler after it's created.
        # This allows the handler to have the neccessary context to unregister itself from within the control functions, while still keeping the control functions simple and stateless.
        handler.bind_controls(unregister, pause, unpause)
        if handler:
            self.handlers.append(handler)
            self.dispatch_cache = {}
        return handler

    def handler(
        self, address: str, validator: type[BaseModel] = OSCMessage
    ) -> Callable[[Callable[P, R_co]], DecoratedHandler[P, R_co]]:
        """Decorator to add a handler for a specfic OSC address pattern.

        Args:
            address (str): The OSC address pattern to match for this handler.
            validator: Add a pydantic validator.
        """

        def handler_decorator(func: Callable[P, R_co]) -> DecoratedHandler[P, R_co]:
            """Registers a handler for a specific OSC address pattern using a decorator syntax, allowing for cleaner and more intuitive handler definitions.

            Args:
                func (Callable[P, R_co]): The function to call when a message matching the address is received. This function can have any signature, and the dispatcher will handle calling it with the correct arguments based on the validated message.

            Returns:
                DecoratedHandler[P, R_co]: The decorated handler function.
            """
            handler = Handler.from_address(address, func, validator)
            self.handlers.append(handler)
            self.dispatch_cache = {}

            def unregister() -> None:
                """Permanently unregisters the handler from the dispatcher."""
                with self.dispatch_lock:
                    if handler in self.handlers:
                        self.handlers.remove(handler)
                        self.dispatch_cache = {}

            def pause() -> None:
                """Temporaily disables a handler"""
                with self.dispatch_lock:
                    if handler.enabled:
                        handler.enabled = False
                    else:
                        warnings.warn(
                            f"Handler for address pattern '{address}' is already paused.",
                            stacklevel=2,
                        )

            def unpause() -> None:
                """Re-enables a previously disabled handler"""
                with self.dispatch_lock:
                    if not handler.enabled:
                        handler.enabled = True
                    else:
                        warnings.warn(
                            f"Handler for address pattern '{address}' is already unpaused.",
                            stacklevel=2,
                        )

            ## Attach the control functions to the decorated function, allowing users to manage their handlers directly from the decorated function reference.
            setattr(func, "unregister", unregister)
            setattr(func, "pause", pause)
            setattr(func, "unpause", unpause)

            return cast(DecoratedHandler[P, R_co], func)

        return handler_decorator

    def toggle_handler(self, address: str, enabled: bool | None = None):
        """Enable or disable a handler for a specific OSC address pattern.

        Args:
            address (str): The OSC address pattern of the handler to toggle.
            enabled (bool): Whether to enable (True) or disable (False) the handler. If None, it will toggle the current state.
        """
        changed_handlers = 0
        with self.dispatch_lock:
            for handler in self.handlers:
                if handler.pattern.pattern == address:
                    changed_handlers += 1
                    if enabled is None:
                        if not handler.enabled:
                            handler.enabled = True
                        else:
                            handler.enabled = False
                    else:
                        handler.enabled = enabled
            self.dispatch_cache = {}
            if changed_handlers == 0:
                raise ValueError(f"No handlers found for address pattern: {address}")

    def start_scheduler(self):
        """Start the background thread for processing timestamped bundles."""
        if self._scheduler_thread is None or not self._scheduler_thread.is_alive():
            self._stop_scheduler.clear()
            self._scheduler_thread = Thread(target=self._scheduler_worker, daemon=True)
            self._scheduler_thread.start()
            # Give the thread a moment to start
            time.sleep(0.001)

    def stop_scheduler(self):
        """Stop the background scheduler thread."""
        self._stop_scheduler.set()
        if self._scheduler_thread and self._scheduler_thread.is_alive():
            self._scheduler_thread.join(timeout=1)

    def _scheduler_worker(self):
        """Background worker that processes scheduled bundles at their timetags."""
        while not self._stop_scheduler.is_set():
            bundle_to_process = None
            with self._scheduler_lock:
                if self._scheduled_heap:
                    scheduled_time, _, bundle = self._scheduled_heap[0]
                    current_time = time.time()
                    if current_time >= scheduled_time:
                        heapq.heappop(self._scheduled_heap)
                        bundle_to_process = bundle

            # Process bundle outside the lock to avoid deadlock
            if bundle_to_process:
                self._process_bundle_immediate(bundle_to_process)
            else:
                time.sleep(0.001)  # Small sleep to prevent busy waiting

    def remove_handler(self, handler: Handler):
        """Removes a specific handler from the dispatcher.

        Args:
            handler (Handler): The handler instance to remove.
        """
        with self.dispatch_lock:
            if handler in self.handlers:
                self.handlers.remove(handler)
                self.dispatch_cache = {}
            else:
                warnings.warn("Handler not found in dispatcher, cannot remove.", stacklevel=2)

    def remove_handler_by_address(self, address: str):
        """
        Removes a handler for a specific OSC address.
        - ``address``: The OSC address to remove the handler for.
        """
        removed_handlers: list[Handler] = []
        with self.dispatch_lock:
            for handler in self.handlers:
                if handler.pattern.pattern == address:
                    removed_handlers.append(handler)

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
                    if handler.enabled:
                        try:
                            handler.run(message)
                        except Exception as e:
                            ## Emit a warning using the built in library event handlers
                            self.error_emit(f"Error in handler for address pattern '{handler.pattern.pattern}': {e}")
                return

        matched_handlers: list[Handler] = []
        with self.dispatch_lock:
            for handler in self.handlers:
                if handler.matches(message.address):
                    matched_handlers.append(handler)
            self.dispatch_cache[message.address] = tuple(matched_handlers)

        for handler in matched_handlers:
            if handler.enabled:
                try:
                    handler.run(message)
                except Exception as e:
                    ## Emit a warning using the built in library event handlers
                    self.error_emit(f"Error in handler for address pattern '{handler.pattern.pattern}': {e}")

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
                # Ensure scheduler is running BEFORE adding to heap
                self.start_scheduler()
                with self._scheduler_lock:
                    self._scheduler_counter += 1
                    heapq.heappush(
                        self._scheduled_heap,
                        (bundle_time, self._scheduler_counter, bundle),
                    )

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
                        matched_handlers: list[Handler] = []
                        for handler in self.handlers:
                            if handler.matches(item.address):
                                matched_handlers.append(handler)
                        handlers = tuple(matched_handlers)
                        self.dispatch_cache[item.address] = handlers

                    # Execute all handlers for this message
                    for handler in handlers:
                        if handler.enabled:
                            try:
                                handler.run(item)
                            except Exception as e:
                                ## Emit a warning using the built in library event handlers
                                self.error_emit(f"Error in handler for address pattern '{handler.pattern.pattern}': {e}")
                elif isinstance(item, OSCBundle):
                    # Nested bundle - check its timetag and either process or schedule
                    # RLock allows the same thread to acquire the lock again
                    if item.timetag == 0:
                        # Immediate nested bundle
                        self._process_bundle_immediate(item)
                    else:
                        # Convert NTP timestamp to Unix timestamp
                        OSC_EPOCH_OFFSET = 2208988800
                        ntp_seconds = item.timetag >> 32
                        ntp_fraction = item.timetag & 0xFFFFFFFF
                        bundle_time = (ntp_seconds - OSC_EPOCH_OFFSET) + (ntp_fraction / (2**32))
                        current_time = time.time()

                        if bundle_time <= current_time:
                            # Time has passed or is now, process immediately
                            self._process_bundle_immediate(item)
                        else:
                            # Schedule nested bundle for future execution
                            self.start_scheduler()
                            with self._scheduler_lock:
                                self._scheduler_counter += 1
                                heapq.heappush(
                                    self._scheduled_heap,
                                    (bundle_time, self._scheduler_counter, item),
                                )
