"""Send a screendump command to the QEMU human monitor socket and convert to PNG.

Writes the VGA framebuffer to a PPM on the GHA runner host, then converts to
PNG using Python stdlib (struct + zlib) — no ImageMagick or ffmpeg needed.
Used as a fallback screenshot mechanism when in-VM methods (grim, gdbus)
are unavailable due to mutter running in software-rendering mode.

Usage: python3 qemu_screendump.py <output.png>
"""
import os
import socket
import struct
import sys
import time
import zlib

SOCK_PATH = '/tmp/qemu-monitor.sock'
PPM_PATH = '/tmp/qemu-desktop.ppm'


def _send_screendump():
    s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    s.settimeout(15)
    s.connect(SOCK_PATH)
    time.sleep(0.5)
    try:
        s.recv(4096)  # discard QEMU monitor greeting
    except socket.timeout:
        pass
    s.send(('screendump ' + PPM_PATH + '\n').encode())
    time.sleep(5)  # wait for QEMU to flush the framebuffer to disk
    s.close()
    print('screendump command sent to QEMU monitor', flush=True)


def _ppm_to_png(ppm_path, png_path):
    """Convert a P6 PPM file to PNG using only Python stdlib (struct + zlib)."""
    with open(ppm_path, 'rb') as f:
        magic = f.readline().strip()
        if magic != b'P6':
            raise ValueError('not a P6 PPM: ' + repr(magic))
        # skip comment lines
        line = ''
        while True:
            line = f.readline().decode('ascii').strip()
            if not line.startswith('#'):
                break
        w, h = map(int, line.split())
        _maxval = int(f.readline().decode('ascii').strip())
        data = f.read()

    # Build PNG: each row has a 1-byte filter (0 = None) followed by RGB pixels
    rows = bytearray()
    row_bytes = w * 3
    for y in range(h):
        rows.append(0)  # filter byte
        rows.extend(data[y * row_bytes:(y + 1) * row_bytes])
    compressed = zlib.compress(bytes(rows), 6)

    def _chunk(name: bytes, payload: bytes) -> bytes:
        crc = zlib.crc32(name + payload) & 0xFFFFFFFF
        return struct.pack('>I', len(payload)) + name + payload + struct.pack('>I', crc)

    png = (
        b'\x89PNG\r\n\x1a\n'
        + _chunk(b'IHDR', struct.pack('>IIBBBBB', w, h, 8, 2, 0, 0, 0))
        + _chunk(b'IDAT', compressed)
        + _chunk(b'IEND', b'')
    )
    with open(png_path, 'wb') as f:
        f.write(png)
    print('PNG written (' + str(len(png)) + ' bytes): ' + png_path, flush=True)


def main():
    png_out = sys.argv[1] if len(sys.argv) > 1 else None

    try:
        _send_screendump()
    except Exception as exc:
        print('QEMU monitor connect/send error: ' + str(exc), flush=True)
        sys.exit(1)

    if not os.path.exists(PPM_PATH):
        print('WARNING: ' + PPM_PATH + ' not found after screendump', flush=True)
        sys.exit(1)

    print('screendump size: ' + str(os.path.getsize(PPM_PATH)) + ' bytes', flush=True)

    if png_out:
        try:
            _ppm_to_png(PPM_PATH, png_out)
        except Exception as exc:
            print('PPM to PNG conversion error: ' + str(exc), flush=True)
            sys.exit(1)


if __name__ == '__main__':
    main()
