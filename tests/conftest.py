"""Shared pytest fixtures and configuration for PyOSC tests."""

import socket
import time
from typing import Generator

import pytest
from oscparser import OSCEncoder, OSCFraming, OSCModes


@pytest.fixture
def free_tcp_port() -> int:
    """Get a free TCP port for testing."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


@pytest.fixture
def free_udp_port() -> int:
    """Get a free UDP port for testing."""
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


@pytest.fixture
def tcp_server(free_tcp_port) -> Generator[tuple[socket.socket, int], None, None]:
    """Create a TCP server socket for testing.

    Yields:
        tuple: (socket, port) pair
    """
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind(("127.0.0.1", free_tcp_port))
    server.listen(1)

    try:
        yield server, free_tcp_port
    finally:
        server.close()


@pytest.fixture
def udp_server(free_udp_port) -> Generator[tuple[socket.socket, int], None, None]:
    """Create a UDP server socket for testing.

    Yields:
        tuple: (socket, port) pair
    """
    server = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    server.bind(("127.0.0.1", free_udp_port))
    server.settimeout(1.0)

    try:
        yield server, free_udp_port
    finally:
        server.close()


@pytest.fixture
def osc_encoder_tcp() -> OSCEncoder:
    """Get an OSC encoder for TCP mode."""
    return OSCEncoder(mode=OSCModes.TCP, framing=OSCFraming.OSC10)


@pytest.fixture
def osc_encoder_udp() -> OSCEncoder:
    """Get an OSC encoder for UDP mode."""
    return OSCEncoder(mode=OSCModes.UDP, framing=OSCFraming.OSC10)


def wait_for_condition(condition_func, timeout=1.0, interval=0.01):
    """Wait for a condition to become true.

    Args:
        condition_func: Callable that returns True when condition is met
        timeout: Maximum time to wait in seconds
        interval: Time between checks in seconds

    Returns:
        bool: True if condition was met, False if timeout
    """
    end_time = time.time() + timeout
    while time.time() < end_time:
        if condition_func():
            return True
        time.sleep(interval)
    return False
