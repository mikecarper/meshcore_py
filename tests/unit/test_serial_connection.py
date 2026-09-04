import asyncio

import pytest

from meshcore import serial_cx
from meshcore.serial_cx import SerialConnection


class RecordingReader:
    def __init__(self):
        self.frames = []

    async def handle_rx(self, data):
        self.frames.append(bytes(data))


class FakeSerial:
    def __init__(self):
        self.dtr = True
        self.rts = True


class FakeTransport:
    def __init__(self):
        self.serial = FakeSerial()


def test_connection_made_preserves_serial_control_lines(monkeypatch):
    monkeypatch.setattr(serial_cx.serial_asyncio, "SerialTransport", FakeTransport)
    conn = SerialConnection("/dev/null", 115200)
    transport = FakeTransport()

    conn.MCSerialClientProtocol(conn).connection_made(transport)

    assert transport.serial.dtr is True
    assert transport.serial.rts is True
    assert conn.transport is transport
    assert conn._connected_event.is_set()


@pytest.mark.asyncio
async def test_handle_rx_discards_leading_junk_before_frame_start():
    conn = SerialConnection("/dev/null", 115200)
    reader = RecordingReader()
    conn.set_reader(reader)

    payload = b"\x00\x01\x02\x53"
    frame = b"\x3e" + len(payload).to_bytes(2, "little") + payload

    conn.handle_rx(b"junk bytes\r\n" + frame)
    await asyncio.sleep(0)

    assert reader.frames == [payload]
    assert conn.header == b""
    assert conn.inframe == b""
    assert conn.frame_expected_size == 0
