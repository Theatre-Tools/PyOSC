"""Integration tests for the current PyOSC workflow."""

import unittest

from oscparser import OSCFraming, OSCMessage, OSCString, OSCTransport

from pyosc.peer import Peer


class TestPeerIntegration(unittest.TestCase):
    """Integration-style tests around the current Peer API."""

    def test_peer_dispatcher_routes_registered_handlers(self):
        """A peer should route messages through its dispatcher once handlers are registered."""
        peer = Peer(
            bind_ip="127.0.0.1",
            bind_port=0,
            remote_address="127.0.0.1",
            remote_port=9000,
            transport=OSCTransport.UDP,
            framing=OSCFraming.OSC10,
            learning=True,
        )

        received = []

        def handle_message(message):
            received.append(message)

        peer.register_handler("/integration/test", handle_message, OSCMessage)
        peer.dispatcher.dispatch(OSCMessage(address="/integration/test", args=(OSCString(value="ok"),)))

        self.assertEqual(len(received), 1)
        self.assertEqual(received[0].address, "/integration/test")


if __name__ == "__main__":
    unittest.main()
