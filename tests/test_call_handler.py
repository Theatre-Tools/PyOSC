"""Unit tests for the CallHandler class."""

import queue
import unittest
from unittest.mock import Mock

from oscparser import OSCInt, OSCMessage
from pydantic import BaseModel, Field

from pyosc.call_handler import Call, CallHandler, CallHandler_Response
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
        call = Call(q, OSCMessage)

        self.assertIs(call.queue, q)
        self.assertEqual(call.validator, OSCMessage)


class TestCallHandler(unittest.TestCase):
    """Test cases for the CallHandler class."""

    def setUp(self):
        """Set up test fixtures."""
        self.mock_peer = Mock(spec=Peer)
        self.mock_peer.dispatcher = Dispatcher(error_emit=lambda _message: None)
        self.mock_peer.connection = Mock()
        self.mock_peer._emit_error = Mock()
        self.call_handler = CallHandler(self.mock_peer)

    def tearDown(self):
        """Clean up after tests."""
        if hasattr(self, "call_handler"):
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

        def mock_send(msg):
            response = OSCMessage(address="/test/call", args=(OSCInt(value=100),))
            self.call_handler(response)

        self.mock_peer.connection.send.side_effect = mock_send

        result = self.call_handler.call(message, timeout=1.0)

        assert result is not None
        assert not isinstance(result, list)
        self.assertIsInstance(result.message, OSCMessage)
        self.assertEqual(result.message.address, "/test/call")

    def test_call_with_custom_return_address(self):
        """Test call with custom return address."""
        message = OSCMessage(address="/test/request", args=())

        def mock_send(msg):
            response = OSCMessage(address="/test/response", args=())
            self.call_handler(response)

        self.mock_peer.connection.send.side_effect = mock_send

        result = self.call_handler.call(message, message_return_address="/test/response", timeout=1.0)

        assert result is not None
        assert not isinstance(result, list)
        self.assertEqual(result.message.address, "/test/response")

    def test_call_with_validator(self):
        """Test call with custom validator."""
        message = OSCMessage(address="/test/validated", args=())

        def mock_send(msg):
            response = OSCMessage(address="/test/validated", args=())
            self.call_handler(response)

        self.mock_peer.connection.send.side_effect = mock_send

        result = self.call_handler.call(message, validator=ResponseModel, timeout=1.0)

        assert result is not None
        assert not isinstance(result, list)
        self.assertIsInstance(result.message, ResponseModel)
        self.assertEqual(result.message.address, "/test/validated")
        self.assertEqual(result.message.status, "success")

    def test_call_multiple_responses(self):
        """Test call requesting multiple responses."""
        message = OSCMessage(address="/test/multi", args=(OSCInt(value=1),))

        def mock_send(msg):
            self.call_handler(OSCMessage(address="/test/multi", args=(OSCInt(value=10),)))
            self.call_handler(OSCMessage(address="/test/multi", args=(OSCInt(value=20),)))

        self.mock_peer.connection.send.side_effect = mock_send

        result = self.call_handler.call(message, max_responses=2, timeout=1.0)

        assert isinstance(result, list)
        self.assertEqual(len(result), 2)
        self.assertTrue(all(isinstance(item, CallHandler_Response) for item in result))
        self.assertTrue(all(isinstance(item.message, OSCMessage) for item in result))

    def test_call_timeout(self):
        """Test call timeout when no response is received."""
        message = OSCMessage(address="/test/timeout", args=())

        self.mock_peer.connection.send.return_value = None

        result = self.call_handler.call(message, timeout=0.1)

        self.assertIsNone(result)
        self.assertEqual(len(self.call_handler.queues), 0)

    def test_call_handler_callable(self):
        """Test CallHandler as callable (message handler)."""
        test_pattern = Handler.pattern_generator("/test")
        test_queue = queue.Queue()
        with self.call_handler.queue_lock:
            self.call_handler.queues[test_pattern] = Call(test_queue, OSCMessage)

        message = OSCMessage(address="/test", args=(OSCInt(value=42),))
        self.call_handler(message)

        self.assertFalse(test_queue.empty())
        result = test_queue.get(timeout=0.1)
        self.assertIsInstance(result, OSCMessage)
        self.assertEqual(result.address, "/test")

    def test_call_handler_validation_error(self):
        """Test validation errors are surfaced through the peer error handler."""

        class StrictModel(BaseModel):
            required_field: str

        test_pattern = Handler.pattern_generator("/test")
        test_queue = queue.Queue()
        with self.call_handler.queue_lock:
            self.call_handler.queues[test_pattern] = Call(test_queue, StrictModel)

        message = OSCMessage(address="/test", args=())
        self.call_handler(message)

        self.assertTrue(test_queue.empty())
        self.mock_peer._emit_error.assert_called_once()

    def test_cleanup_after_successful_call(self):
        """Test queues are cleaned up after a successful call."""
        message = OSCMessage(address="/test/cleanup", args=())

        def mock_send(msg):
            response = OSCMessage(address="/test/cleanup", args=())
            self.call_handler(response)

        self.mock_peer.connection.send.side_effect = mock_send

        result = self.call_handler.call(message, timeout=1.0)

        assert result is not None
        assert not isinstance(result, list)
        self.assertEqual(len(self.call_handler.queues), 0)


if __name__ == "__main__":
    unittest.main()
