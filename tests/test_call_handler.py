"""Unit tests for the CallHandler class."""

import queue
import time
import unittest
from typing import cast
from unittest.mock import MagicMock, Mock

from oscparser import OSCInt, OSCMessage, OSCString
from pydantic import BaseModel, Field

from pyosc.call_handler import Call, CallHandler, CallHandler_Response, CallHandlerValidationError
from pyosc.dispatcher import Dispatcher
from pyosc.handler import Handler
from pyosc.peer import Peer


class ResponseModel(BaseModel):
    """Custom response model for testing."""

    address: str
    args: tuple
    status: str = Field(default="success")


class TestCall(unittest.TestCase):
    """Test cases for the Call class."""

    def test_call_initialization(self):
        """Test Call object initialization."""
        q = queue.Queue()
        call = Call(q, OSCMessage, prefix=2)

        self.assertIs(call.queue, q)
        self.assertEqual(call.validator, OSCMessage)
        self.assertEqual(call.prefix_remaining, 2)


class TestCallHandler(unittest.TestCase):
    """Test cases for the CallHandler class."""

    def setUp(self):
        """Set up test fixtures."""
        self.mock_peer = Mock(spec=Peer)
        self.mock_peer.dispatcher = Dispatcher(error_emit=lambda _message: None)
        dispatcher = self.mock_peer.dispatcher
        original_remove_handler = dispatcher.remove_handler

        def add_handler(address, handler, validator=OSCMessage):
            return dispatcher.register_handler(address, handler, validator)

        def remove_handler(address_or_handler):
            if isinstance(address_or_handler, str):
                dispatcher.remove_handler_by_address(address_or_handler)
            else:
                original_remove_handler(address_or_handler)

        dispatcher.add_handler = add_handler  # type: ignore[attr-defined]
        dispatcher.remove_handler = remove_handler  # type: ignore[attr-defined]

        # Dynamically create mock handlers with patterns based on address
        def register_handler_side_effect(address, handler, validator=OSCMessage):
            mock_handler = Mock()
            mock_handler.pattern = Handler.pattern_generator(address)
            mock_handler.unregister = Mock()
            return mock_handler

        self.mock_peer.register_handler.side_effect = register_handler_side_effect
        self.call_handler = CallHandler(self.mock_peer)

    def tearDown(self):
        """Clean up after tests."""
        if hasattr(self, "call_handler"):
            # Clear any remaining queues
            with self.call_handler.queue_lock:
                self.call_handler.queues.clear()

    def test_initialization(self):
        """Test CallHandler initialization."""
        self.assertIs(self.call_handler.peer, self.mock_peer)
        self.assertEqual(len(self.call_handler.queues), 0)
        self.assertIsNotNone(self.call_handler.queue_lock)

    def test_call_basic_success(self):
        """Test basic call with successful response."""
        message = OSCMessage(address="/test/call", args=(OSCInt(value=42),))

        # Mock send_message
        def mock_send(msg):
            # Simulate receiving response
            response = OSCMessage(address="/test/call", args=(OSCInt(value=100),))
            self.call_handler(response)

        self.mock_peer.send_message = mock_send

        result = self.call_handler.call(message, timeout=1.0)

        self.assertIsNotNone(result)
        self.assertIsInstance(result, CallHandler_Response)
        if not isinstance(result, CallHandler_Response):
            self.fail("Expected CallHandler_Response")
        self.assertIsInstance(result.message, OSCMessage)
        self.assertEqual(result.message.address, "/test/call")

    def test_call_with_custom_return_address(self):
        """Test call with custom return address."""
        message = OSCMessage(address="/test/request", args=())

        def mock_send(msg):
            # Send response to custom address
            response = OSCMessage(address="/test/response", args=(OSCString(value="ok"),))
            self.call_handler(response)

        self.mock_peer.send_message = mock_send

        result = self.call_handler.call(message, return_address="/test/response", timeout=1.0)

        self.assertIsNotNone(result)
        self.assertIsInstance(result, CallHandler_Response)
        if not isinstance(result, CallHandler_Response):
            self.fail("Expected CallHandler_Response")
        self.assertEqual(result.message.address, "/test/response")

    def test_call_with_validator(self):
        """Test call with custom validator."""
        message = OSCMessage(address="/test/validated", args=())

        def mock_send(msg):
            response = OSCMessage(
                address="/test/validated",
                args=(OSCString(value="success"),),
            )
            self.call_handler(response)

        self.mock_peer.send_message = mock_send

        result = self.call_handler.call(message, validator=ResponseModel, timeout=1.0)

        self.assertIsNotNone(result)
        self.assertIsInstance(result, CallHandler_Response)
        if not isinstance(result, CallHandler_Response):
            self.fail("Expected CallHandler_Response")
        self.assertIsInstance(result.message, ResponseModel)
        self.assertEqual(result.message.address, "/test/validated")
        self.assertEqual(result.message.status, "success")

    def test_call_multiple_responses(self):
        """Test call requesting multiple responses."""
        message = OSCMessage(address="/test/multi", args=(OSCInt(value=1),))

        def mock_send(msg):
            self.call_handler(OSCMessage(address="/test/multi", args=(OSCInt(value=10),)))
            self.call_handler(OSCMessage(address="/test/multi", args=(OSCInt(value=20),)))

        self.mock_peer.send_message = mock_send

        result = self.call_handler.call(message, responses=2, timeout=1.0)

        self.assertIsInstance(result, list)
        assert isinstance(result, list)
        self.assertEqual(len(result), 2)
        self.assertTrue(all(isinstance(item, CallHandler_Response) for item in result))
        self.assertTrue(all(isinstance(item.message, OSCMessage) for item in result))

    def test_unregister_called_after_successful_call(self):
        """Test handler is always unregistered after a successful call."""
        message = OSCMessage(address="/test/unregister/success", args=())

        mock_handlers = []
        original_side_effect = self.mock_peer.register_handler.side_effect

        def capture_handler_side_effect(address, handler, validator=OSCMessage):
            result = original_side_effect(address, handler, validator)
            mock_handlers.append(result)
            return result

        self.mock_peer.register_handler.side_effect = capture_handler_side_effect

        def mock_send(msg):
            self.call_handler(OSCMessage(address="/test/unregister/success", args=()))

        self.mock_peer.send_message = mock_send

        result = self.call_handler.call(message, timeout=1.0)

        self.assertIsNotNone(result)
        self.assertEqual(len(mock_handlers), 1)
        mock_handlers[0].unregister.assert_called_once()

    def test_unregister_called_after_timeout(self):
        """Test handler is always unregistered after a timeout."""
        message = OSCMessage(address="/test/unregister/timeout", args=())

        mock_handlers = []
        original_side_effect = self.mock_peer.register_handler.side_effect

        def capture_handler_side_effect(address, handler, validator=OSCMessage):
            result = original_side_effect(address, handler, validator)
            mock_handlers.append(result)
            return result

        self.mock_peer.register_handler.side_effect = capture_handler_side_effect
        self.mock_peer.send_message = MagicMock()

        result = self.call_handler.call(message, timeout=0.1)

        self.assertIsNone(result)
        self.assertEqual(len(mock_handlers), 1)
        mock_handlers[0].unregister.assert_called_once()

    def test_call_timeout(self):
        """Test call timeout when no response received."""
        message = OSCMessage(address="/test/timeout", args=())

        # Don't send any response
        self.mock_peer.send_message = MagicMock()

        result = self.call_handler.call(message, timeout=0.1)

        self.assertIsNone(result)
        # Queue should be cleaned up
        self.assertEqual(len(self.call_handler.queues), 0)

    def test_call_handler_callable(self):
        """Test CallHandler as callable (message handler)."""
        # Create a pattern for the test address
        test_pattern = Handler.pattern_generator("/test")
        test_queue = queue.Queue()
        with self.call_handler.queue_lock:
            self.call_handler.queues[test_pattern] = Call(test_queue, OSCMessage)

        # Call the handler
        message = OSCMessage(address="/test", args=(OSCInt(value=42),))
        self.call_handler(message)

        # Check queue received message
        self.assertFalse(test_queue.empty())
        result = test_queue.get(timeout=0.1)
        self.assertIsInstance(result, OSCMessage)
        self.assertEqual(result.address, "/test")

    def test_call_handler_wrong_address(self):
        """Test CallHandler ignores messages with wrong address."""
        # Create a pattern for /test
        test_pattern = Handler.pattern_generator("/test")
        test_queue = queue.Queue()
        with self.call_handler.queue_lock:
            self.call_handler.queues[test_pattern] = Call(test_queue, OSCMessage)

        # Send message to different address
        message = OSCMessage(address="/other", args=())
        self.call_handler(message)

        # Queue should remain empty
        self.assertTrue(test_queue.empty())

    def test_call_handler_validation_error(self):
        """Test CallHandler handles validation errors gracefully."""

        class StrictModel(BaseModel):
            required_field: str

        test_pattern = Handler.pattern_generator("/test")
        test_queue = queue.Queue()
        with self.call_handler.queue_lock:
            self.call_handler.queues[test_pattern] = Call(test_queue, StrictModel)

        # Send message that won't validate
        message = OSCMessage(address="/test", args=())

        with self.assertRaises(CallHandlerValidationError):
            self.call_handler(message)

        # Queue should remain empty
        self.assertTrue(test_queue.empty())

    def test_call_handler_prefix_skips_validation(self):
        """Test prefixed messages are ignored before validation."""

        class StrictModel(BaseModel):
            required_field: str

        test_pattern = Handler.pattern_generator("/test")
        test_queue = queue.Queue()
        with self.call_handler.queue_lock:
            self.call_handler.queues[test_pattern] = Call(test_queue, StrictModel, prefix=1)

        # First invalid message should be ignored and not validated.
        message = OSCMessage(address="/test", args=())
        self.call_handler(message)
        self.assertTrue(test_queue.empty())

        # Next message should be validated and fail.
        with self.assertRaises(CallHandlerValidationError):
            self.call_handler(message)

    def test_call_prefix_ignores_initial_responses(self):
        """Test call() ignores prefixed messages before collecting responses."""
        message = OSCMessage(address="/test/prefix", args=())

        def mock_send(msg):
            self.call_handler(OSCMessage(address="/test/prefix", args=(OSCString(value="ignore-me"),)))
            self.call_handler(OSCMessage(address="/test/prefix", args=(OSCString(value="use-me"),)))

        self.mock_peer.send_message = mock_send

        result = self.call_handler.call(message, timeout=1.0, prefix=1)

        self.assertIsNotNone(result)
        self.assertIsInstance(result, CallHandler_Response)
        if not isinstance(result, CallHandler_Response):
            self.fail("Expected CallHandler_Response")
        self.assertIsInstance(result.message, OSCMessage)
        self.assertEqual(result.message.address, "/test/prefix")
        self.assertEqual(len(result.message.args), 1)
        arg = result.message.args[0]
        self.assertIsInstance(arg, OSCString)
        self.assertEqual(cast(OSCString, arg).value, "use-me")

    def test_call_prefix_with_multiple_responses(self):
        """Test responses count is interpreted after applying prefix."""
        message = OSCMessage(address="/test/prefix/multi", args=())

        def mock_send(msg):
            self.call_handler(OSCMessage(address="/test/prefix/multi", args=(OSCString(value="ignore"),)))
            self.call_handler(OSCMessage(address="/test/prefix/multi", args=(OSCString(value="first"),)))
            self.call_handler(OSCMessage(address="/test/prefix/multi", args=(OSCString(value="second"),)))

        self.mock_peer.send_message = mock_send

        result = self.call_handler.call(message, timeout=1.0, prefix=1, responses=2)

        self.assertIsInstance(result, CallHandler_Response)
        if not isinstance(result, CallHandler_Response):
            self.fail("Expected CallHandler_Response")
        arg = result.message.args[0]
        self.assertIsInstance(arg, OSCString)
        self.assertEqual(cast(OSCString, arg).value, "first")

    def test_concurrent_calls(self):
        """Test multiple concurrent calls to different addresses."""
        messages = [OSCMessage(address=f"/test/call{i}", args=(OSCInt(value=i),)) for i in range(5)]

        results = []
        responses_sent = []

        def mock_send(msg):
            # Store for later
            responses_sent.append(msg)

        self.mock_peer.send_message = mock_send

        # Start calls in threads
        import threading

        def make_call(msg, idx):
            # Simulate delayed response
            def delayed_response():
                time.sleep(0.05)
                response = OSCMessage(address=msg.address, args=(OSCInt(value=idx * 10),))
                self.call_handler(response)

            threading.Thread(target=delayed_response, daemon=True).start()

            result = self.call_handler.call(msg, timeout=1.0)
            results.append((idx, result))

        threads = []
        for i, msg in enumerate(messages):
            t = threading.Thread(target=make_call, args=(msg, i))
            threads.append(t)
            t.start()

        # Wait for all threads
        for t in threads:
            t.join()

        # All calls should succeed
        self.assertEqual(len(results), 5)
        for idx, result in results:
            self.assertIsNotNone(result)
            assert result is not None
            self.assertIsInstance(result, CallHandler_Response)
            self.assertIsInstance(result.message, OSCMessage)

    def test_queue_lock_thread_safety(self):
        """Test that queue_lock prevents race conditions."""
        iterations = 100
        errors = []

        def add_remove_queue():
            for i in range(iterations):
                try:
                    pattern = Handler.pattern_generator(f"/test/{i}")
                    with self.call_handler.queue_lock:
                        self.call_handler.queues[pattern] = Call(queue.Queue(), OSCMessage)
                    with self.call_handler.queue_lock:
                        if pattern in self.call_handler.queues:
                            del self.call_handler.queues[pattern]
                except Exception as e:
                    errors.append(e)

        import threading

        threads = [threading.Thread(target=add_remove_queue) for _ in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # Should have no errors
        self.assertEqual(len(errors), 0)

    def test_cleanup_after_successful_call(self):
        """Test that queues and handlers are cleaned up after successful call."""
        message = OSCMessage(address="/test/cleanup", args=())

        def mock_send(msg):
            response = OSCMessage(address="/test/cleanup", args=())
            self.call_handler(response)

        self.mock_peer.send_message = mock_send

        result = self.call_handler.call(message, timeout=1.0)

        self.assertIsNotNone(result)
        # Queue should be cleaned up
        self.assertEqual(len(self.call_handler.queues), 0)

    def test_cleanup_after_timeout(self):
        """Test that queues are cleaned up after timeout."""
        message = OSCMessage(address="/test/cleanup", args=())
        self.mock_peer.send_message = MagicMock()

        result = self.call_handler.call(message, timeout=0.1)

        self.assertIsNone(result)
        # Queue should be cleaned up
        self.assertEqual(len(self.call_handler.queues), 0)


if __name__ == "__main__":
    unittest.main()
