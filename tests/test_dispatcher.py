"""Unit tests for the Dispatcher class."""

import time
import unittest
from unittest.mock import MagicMock

from oscparser import OSCBundle, OSCInt, OSCMessage
from pydantic import BaseModel

from pyosc.dispatcher import (
    Dispatcher,
    DispatcherMissingFieldError,
    Handler,
)


class CustomModel(BaseModel):
    """Custom model for testing validator."""

    address: str
    args: tuple


class TestHandlerMatcher(unittest.TestCase):
    """Test cases for handler address pattern matching."""

    def test_exact_match(self):
        """Test exact address matching."""
        matcher = Handler.from_address("/test/message", lambda _msg: None, OSCMessage)
        self.assertTrue(matcher.matches("/test/message"))
        self.assertFalse(matcher.matches("/test/other"))
        self.assertFalse(matcher.matches("/test"))

    def test_single_char_wildcard(self):
        """Test ? wildcard matches single character."""
        matcher = Handler.from_address("/test/?", lambda _msg: None, OSCMessage)
        self.assertTrue(matcher.matches("/test/a"))
        self.assertTrue(matcher.matches("/test/1"))
        self.assertFalse(matcher.matches("/test/ab"))
        self.assertFalse(matcher.matches("/test/"))

    def test_multi_char_wildcard(self):
        """Test * wildcard matches zero or more characters."""
        matcher = Handler.from_address("/test/*", lambda _msg: None, OSCMessage)
        self.assertTrue(matcher.matches("/test/"))
        self.assertTrue(matcher.matches("/test/abc"))
        self.assertTrue(matcher.matches("/test/123"))
        self.assertFalse(matcher.matches("/test/abc/def"))

    def test_character_class(self):
        """Test [abc] character class matching."""
        matcher = Handler.from_address("/test/[abc]", lambda _msg: None, OSCMessage)
        self.assertTrue(matcher.matches("/test/a"))
        self.assertTrue(matcher.matches("/test/b"))
        self.assertTrue(matcher.matches("/test/c"))
        self.assertFalse(matcher.matches("/test/d"))

    def test_negated_character_class(self):
        """Test [!abc] negated character class matching."""
        matcher = Handler.from_address("/test/[!abc]", lambda _msg: None, OSCMessage)
        self.assertFalse(matcher.matches("/test/a"))
        self.assertFalse(matcher.matches("/test/b"))
        self.assertTrue(matcher.matches("/test/d"))
        self.assertTrue(matcher.matches("/test/x"))

    def test_alternatives(self):
        """Test {foo,bar} alternatives matching."""
        matcher = Handler.from_address("/test/{foo,bar}", lambda _msg: None, OSCMessage)
        self.assertTrue(matcher.matches("/test/foo"))
        self.assertTrue(matcher.matches("/test/bar"))
        self.assertFalse(matcher.matches("/test/baz"))

    def test_complex_pattern(self):
        """Test complex pattern combining multiple wildcards."""
        matcher = Handler.from_address("/osc/*/[0-9]?/{enable,disable}", lambda _msg: None, OSCMessage)
        self.assertTrue(matcher.matches("/osc/channel/12/enable"))
        self.assertTrue(matcher.matches("/osc/track/5a/disable"))
        self.assertFalse(matcher.matches("/osc/channel/12/toggle"))

    def test_hash_equality(self):
        """Test handler matcher can be hashed."""
        matcher1 = Handler.from_address("/test/message", lambda _msg: None, OSCMessage)
        # Test that they can be used in sets/dicts
        matcher_set = {matcher1}
        self.assertEqual(len(matcher_set), 1)


class TestHandlerValidation(unittest.TestCase):
    """Test handler validation and dispatch behavior."""

    def test_valid_message_dispatch(self):
        """Test successful validation and dispatch."""
        mock_dispatcher = MagicMock()
        handler = Handler.from_address("/test", mock_dispatcher, OSCMessage)

        message = OSCMessage(address="/test", args=())
        handler.run(message)

        mock_dispatcher.assert_called_once()
        called_with = mock_dispatcher.call_args[0][0]
        self.assertIsInstance(called_with, OSCMessage)
        self.assertEqual(called_with.address, "/test")

    def test_validation_error_missing_field(self):
        """Test that missing fields raise a specific validation error."""
        mock_dispatcher = MagicMock()

        class StrictModel(BaseModel):
            required_field: str

        handler = Handler.from_address("/test", mock_dispatcher, StrictModel)

        message = OSCMessage(address="/test", args=())
        with self.assertRaises(DispatcherMissingFieldError):
            handler.run(message)

        # Dispatcher should not be called when validation fails
        mock_dispatcher.assert_not_called()


class TestDispatcher(unittest.TestCase):
    """Test cases for the main Dispatcher class."""

    def setUp(self):
        """Set up test fixtures."""
        self.dispatcher = Dispatcher(error_emit=lambda _message: None)

    def tearDown(self):
        """Clean up after tests."""
        self.dispatcher.stop_scheduler()

    def test_add_handler(self):
        """Test adding a message handler."""
        mock_handler = MagicMock()
        handler = self.dispatcher.register_handler("/test", mock_handler, OSCMessage)

        self.assertEqual(len(self.dispatcher.handlers), 1)
        self.assertTrue(self.dispatcher.handlers[0].matches("/test"))
        self.assertIs(handler, self.dispatcher.handlers[0])

    def test_add_handler_with_validator(self):
        """Test adding a handler with custom validator."""
        mock_handler = MagicMock()
        handler = self.dispatcher.register_handler("/test", mock_handler, CustomModel)

        self.assertEqual(len(self.dispatcher.handlers), 1)
        self.assertIs(handler.validator, CustomModel)

    def test_dispatch_exact_match(self):
        """Test dispatching to exact matching handler."""
        mock_handler = MagicMock()
        self.dispatcher.register_handler("/test/message", mock_handler, OSCMessage)

        message = OSCMessage(address="/test/message", args=())
        self.dispatcher.dispatch(message)

        mock_handler.assert_called_once()

    def test_dispatch_wildcard_match(self):
        """Test dispatching with wildcard patterns."""
        mock_handler = MagicMock()
        self.dispatcher.register_handler("/test/*", mock_handler, OSCMessage)

        message = OSCMessage(address="/test/anything", args=())
        self.dispatcher.dispatch(message)

        mock_handler.assert_called_once()

    def test_dispatch_wildcard_does_not_match_extra_parts(self):
        """Test that * wildcard does not cross slash-delimited address parts."""
        mock_handler = MagicMock()
        self.dispatcher.register_handler("/test/*", mock_handler, OSCMessage)

        message = OSCMessage(address="/test/one/two", args=())
        self.dispatcher.dispatch(message)

        mock_handler.assert_not_called()

    def test_dispatch_multiple_handlers(self):
        """Test dispatching to multiple matching handlers."""
        mock_handler1 = MagicMock()
        mock_handler2 = MagicMock()

        self.dispatcher.register_handler("/test/*", mock_handler1, OSCMessage)
        self.dispatcher.register_handler("/test/message", mock_handler2, OSCMessage)

        message = OSCMessage(address="/test/message", args=())
        self.dispatcher.dispatch(message)

        mock_handler1.assert_called_once()
        mock_handler2.assert_called_once()

    def test_dispatch_no_match(self):
        """Test dispatching with no matching handlers."""
        mock_handler = MagicMock()
        self.dispatcher.register_handler("/other", mock_handler, OSCMessage)

        message = OSCMessage(address="/test/message", args=())
        self.dispatcher.dispatch(message)

        mock_handler.assert_not_called()

    def test_dispatch_cache(self):
        """Test that dispatch cache is used for repeated messages."""
        mock_handler = MagicMock()
        self.dispatcher.register_handler("/test", mock_handler, OSCMessage)

        message = OSCMessage(address="/test", args=())

        # First dispatch should build cache
        self.dispatcher.dispatch(message)
        self.assertIn("/test", self.dispatcher.dispatch_cache)

        # Second dispatch should use cache
        self.dispatcher.dispatch(message)
        self.assertEqual(mock_handler.call_count, 2)

    def test_unregister_handler(self):
        """Test unregistering a handler."""
        mock_handler = MagicMock()
        handler = self.dispatcher.register_handler("/test", mock_handler, OSCMessage)

        # Remove the handler
        handler.unregister()

        message = OSCMessage(address="/test", args=())
        self.dispatcher.dispatch(message)

        mock_handler.assert_not_called()

    def test_unregister_handler_clears_cache(self):
        """Test that unregistering a handler clears the dispatch cache."""
        mock_handler = MagicMock()
        handler = self.dispatcher.register_handler("/test", mock_handler, OSCMessage)

        # Populate cache
        message = OSCMessage(address="/test", args=())
        self.dispatcher.dispatch(message)
        self.assertIn("/test", self.dispatcher.dispatch_cache)

        # Remove handler should clear cache
        handler.unregister()
        self.assertEqual(len(self.dispatcher.dispatch_cache), 0)

    def test_pause_and_unpause_handler(self):
        """Test pausing and unpausing a handler."""
        mock_handler = MagicMock()
        handler = self.dispatcher.register_handler("/test", mock_handler, OSCMessage)

        handler.pause()
        self.assertFalse(handler.enabled)

        message = OSCMessage(address="/test", args=())
        self.dispatcher.dispatch(message)
        mock_handler.assert_not_called()

        handler.unpause()
        self.assertTrue(handler.enabled)

        self.dispatcher.dispatch(message)
        mock_handler.assert_called_once()

    def test_dispatch_bundle_immediate(self):
        """Test dispatching bundle with immediate timetag (0)."""
        mock_handler = MagicMock()
        self.dispatcher.register_handler("/test", mock_handler, OSCMessage)

        bundle = OSCBundle(
            timetag=0,
            elements=(
                OSCMessage(address="/test", args=(OSCInt(value=1),)),
                OSCMessage(address="/test", args=(OSCInt(value=2),)),
            ),
        )

        self.dispatcher.dispatch(bundle)

        self.assertEqual(mock_handler.call_count, 2)

    def test_dispatch_bundle_nested(self):
        """Test dispatching nested bundles."""
        mock_handler = MagicMock()
        self.dispatcher.register_handler("/test", mock_handler, OSCMessage)

        inner_bundle = OSCBundle(
            timetag=0,
            elements=(OSCMessage(address="/test", args=(OSCInt(value=1),)),),
        )

        outer_bundle = OSCBundle(
            timetag=0,
            elements=(
                OSCMessage(address="/test", args=(OSCInt(value=2),)),
                inner_bundle,
            ),
        )

        self.dispatcher.dispatch(outer_bundle)

        self.assertEqual(mock_handler.call_count, 2)

    def test_dispatch_bundle_past_timetag(self):
        """Test bundle with past timetag is processed immediately."""
        mock_handler = MagicMock()
        self.dispatcher.register_handler("/test", mock_handler, OSCMessage)

        # Create a timetag for 1 second in the past
        # NTP timestamp format: (seconds << 32) | fraction
        OSC_EPOCH_OFFSET = 2208988800
        past_time = int(time.time() - 1) + OSC_EPOCH_OFFSET
        ntp_timetag = past_time << 32

        bundle = OSCBundle(
            timetag=ntp_timetag,
            elements=(OSCMessage(address="/test", args=()),),
        )

        self.dispatcher.dispatch(bundle)

        # Should be processed immediately
        mock_handler.assert_called_once()

    def test_dispatch_bundle_future_timetag(self):
        """Test bundle with future timetag is scheduled."""
        mock_handler = MagicMock()
        self.dispatcher.register_handler("/test", mock_handler, OSCMessage)

        # Create a timetag for 1.0 seconds in the future (more generous timing)
        OSC_EPOCH_OFFSET = 2208988800
        target_time = time.time() + 1.0
        ntp_seconds = int(target_time) + OSC_EPOCH_OFFSET
        ntp_fraction = int((target_time % 1) * (2**32))
        ntp_timetag = (ntp_seconds << 32) | ntp_fraction

        bundle = OSCBundle(
            timetag=ntp_timetag,
            elements=(OSCMessage(address="/test", args=()),),
        )

        self.dispatcher.dispatch(bundle)

        # Small delay to ensure dispatch completes
        time.sleep(0.01)

        # Should not be called immediately
        mock_handler.assert_not_called()

        # Should be in scheduled heap
        self.assertEqual(len(self.dispatcher._scheduled_heap), 1)

        # Wait for scheduled execution
        time.sleep(1.1)

        # Should now be called
        mock_handler.assert_called_once()

    def test_dispatch_bundle_nested_future_timetag(self):
        """Test nested bundle with future timetag is scheduled, not immediate."""
        mock_handler = MagicMock()
        self.dispatcher.register_handler("/test", mock_handler, OSCMessage)

        OSC_EPOCH_OFFSET = 2208988800
        target_time = time.time() + 0.5
        ntp_seconds = int(target_time) + OSC_EPOCH_OFFSET
        ntp_fraction = int((target_time % 1) * (2**32))
        ntp_timetag = (ntp_seconds << 32) | ntp_fraction

        nested_bundle = OSCBundle(
            timetag=ntp_timetag,
            elements=(OSCMessage(address="/test", args=()),),
        )
        outer_bundle = OSCBundle(
            timetag=0,
            elements=(nested_bundle,),
        )

        self.dispatcher.dispatch(outer_bundle)

        # Nested future bundle should not dispatch immediately
        time.sleep(0.01)
        mock_handler.assert_not_called()

        # Should be scheduled and dispatched later
        self.assertEqual(len(self.dispatcher._scheduled_heap), 1)
        time.sleep(0.7)
        mock_handler.assert_called_once()

    def test_dispatch_bundle_nested_past_timetag(self):
        """Test nested bundle with past timetag is processed immediately."""
        mock_handler = MagicMock()
        self.dispatcher.register_handler("/test", mock_handler, OSCMessage)

        OSC_EPOCH_OFFSET = 2208988800
        past_time = int(time.time() - 1) + OSC_EPOCH_OFFSET
        ntp_timetag = past_time << 32

        nested_bundle = OSCBundle(
            timetag=ntp_timetag,
            elements=(OSCMessage(address="/test", args=()),),
        )
        outer_bundle = OSCBundle(
            timetag=0,
            elements=(nested_bundle,),
        )

        self.dispatcher.dispatch(outer_bundle)

        mock_handler.assert_called_once()

    def test_scheduler_start_stop(self):
        """Test scheduler thread lifecycle."""
        self.dispatcher.start_scheduler()
        self.assertIsNotNone(self.dispatcher._scheduler_thread)
        assert self.dispatcher._scheduler_thread is not None  # Type narrowing
        self.assertTrue(self.dispatcher._scheduler_thread.is_alive())

        self.dispatcher.stop_scheduler()
        # Give thread time to stop
        time.sleep(0.05)
        self.assertTrue(self.dispatcher._stop_scheduler.is_set())

    def test_multiple_scheduled_bundles(self):
        """Test multiple scheduled bundles are processed in order."""
        mock_handler = MagicMock()
        self.dispatcher.register_handler("/test", mock_handler, OSCMessage)

        OSC_EPOCH_OFFSET = 2208988800
        # Use time.time() directly with fractional seconds for more precision
        base_time = time.time() + 0.2

        # Schedule three bundles 0.1 seconds apart
        for i in range(3):
            schedule_time = base_time + (i * 0.1)
            ntp_seconds = int(schedule_time) + OSC_EPOCH_OFFSET
            ntp_fraction = int((schedule_time % 1) * (2**32))
            ntp_timetag = (ntp_seconds << 32) | ntp_fraction

            bundle = OSCBundle(
                timetag=ntp_timetag,
                elements=(OSCMessage(address="/test", args=(OSCInt(value=i),)),),
            )
            self.dispatcher.dispatch(bundle)

        # Wait for all to be processed
        time.sleep(0.6)

        self.assertEqual(mock_handler.call_count, 3)


if __name__ == "__main__":
    unittest.main()
