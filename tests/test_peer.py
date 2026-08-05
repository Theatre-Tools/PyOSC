"""Unit tests for the Peer class."""

import unittest

from oscparser import OSCFraming, OSCMessage, OSCTransport

from pyosc.peer import Peer
from pyosc.transport import ConnectionRole


class TestPeer(unittest.TestCase):
    """Test cases for the current Peer API."""

    def test_peer_initializes_transport_and_dispatcher(self):
        """The peer should construct its transport, dispatcher, and call handler."""
        peer = Peer(
            remote_address="127.0.0.1",
            remote_port=9000,
            transport=OSCTransport.TCP,
            framing=OSCFraming.OSC10,
        )

        self.assertIsNotNone(peer.connection)
        self.assertIsNotNone(peer.dispatcher)
        self.assertIsNotNone(peer.callHandler)
        self.assertTrue(callable(peer.send_message))
        self.assertEqual(peer.transport, OSCTransport.TCP)
        self.assertEqual(peer.connection_role, ConnectionRole.INITIATING)

    def test_event_handlers_are_normalized_and_emitted(self):
        """Event handlers should support the current connect/error callback signatures."""
        peer = Peer(
            bind_ip="127.0.0.1",
            bind_port=0,
            remote_address="127.0.0.1",
            remote_port=9000,
            transport=OSCTransport.UDP,
            framing=OSCFraming.OSC10,
            learning=True,
        )

        events = []

        @peer.event
        def on_connect(peer_instance):
            events.append(("connect", peer_instance))

        @peer.event
        def on_error(error):
            events.append(("error", error))

        peer._emit_connection_state(True)
        peer._emit_error(RuntimeError("boom"))

        self.assertEqual(len(events), 2)
        self.assertEqual(events[0][0], "connect")
        self.assertEqual(events[1][0], "error")
        self.assertIs(events[0][1], peer)
        self.assertIsInstance(events[1][1], RuntimeError)

    def test_register_handler_proxies_to_dispatcher(self):
        """Handler registration should be forwarded to the dispatcher."""
        peer = Peer(
            bind_ip="127.0.0.1",
            bind_port=0,
            remote_address="127.0.0.1",
            remote_port=9000,
            transport=OSCTransport.UDP,
            framing=OSCFraming.OSC10,
        )

        def handle_message(message):
            return None

        registered = peer.register_handler("/demo", handle_message, OSCMessage)

        self.assertIn(registered, peer.dispatcher.handlers)

    def test_stop_listening_closes_transport(self):
        """Stopping a peer should mark the stop flag and close its transport."""
        peer = Peer(
            bind_ip="127.0.0.1",
            bind_port=0,
            remote_address="127.0.0.1",
            remote_port=9000,
            transport=OSCTransport.UDP,
            framing=OSCFraming.OSC10,
            learning=True,
        )

        peer.start_listening()
        peer.stop_listening()

        self.assertTrue(peer.stop_flag.is_set())


if __name__ == "__main__":
    unittest.main()
