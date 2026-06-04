"""Unit tests for tests/shared/qemu_screendump.py.

Tests the pure-Python PPM→PNG conversion logic without requiring
a real QEMU monitor socket or filesystem.
"""

import struct
import zlib

import pytest

from tests.shared import qemu_screendump


# ---------------------------------------------------------------------------
# Helpers to build minimal valid P6 PPM bytes
# ---------------------------------------------------------------------------

def _make_ppm(width: int, height: int, fill_rgb: tuple[int, int, int] = (255, 0, 0)) -> bytes:
    """Build a minimal P6 PPM image filled with a single colour."""
    r, g, b = fill_rgb
    header = f"P6\n{width} {height}\n255\n".encode()
    pixels = bytes([r, g, b] * width * height)
    return header + pixels


# ---------------------------------------------------------------------------
# _ppm_to_png — basic round-trip
# ---------------------------------------------------------------------------

def test_ppm_to_png_writes_valid_png_header(tmp_path):
    ppm_path = tmp_path / "test.ppm"
    png_path = tmp_path / "test.png"
    ppm_path.write_bytes(_make_ppm(4, 4))

    qemu_screendump._ppm_to_png(str(ppm_path), str(png_path))

    data = png_path.read_bytes()
    assert data[:8] == b"\x89PNG\r\n\x1a\n", "output does not start with PNG magic bytes"


def test_ppm_to_png_ihdr_contains_correct_dimensions(tmp_path):
    w, h = 8, 6
    ppm_path = tmp_path / "test.ppm"
    png_path = tmp_path / "out.png"
    ppm_path.write_bytes(_make_ppm(w, h))

    qemu_screendump._ppm_to_png(str(ppm_path), str(png_path))

    data = png_path.read_bytes()
    # IHDR starts at offset 8: 4-byte length, 4-byte "IHDR", then payload
    ihdr_payload = data[16:29]  # 13 bytes: width(4)+height(4)+bitdepth+colortype+...
    got_w, got_h = struct.unpack(">II", ihdr_payload[:8])
    assert got_w == w
    assert got_h == h


def test_ppm_to_png_idat_chunk_decompresses_without_error(tmp_path):
    ppm_path = tmp_path / "test.ppm"
    png_path = tmp_path / "out.png"
    ppm_path.write_bytes(_make_ppm(2, 2, fill_rgb=(0, 128, 255)))

    qemu_screendump._ppm_to_png(str(ppm_path), str(png_path))

    data = png_path.read_bytes()
    # Locate IDAT chunk: skip PNG sig(8) + IHDR chunk(4+4+13+4=25)
    idat_offset = 8 + 25
    idat_len = struct.unpack(">I", data[idat_offset : idat_offset + 4])[0]
    idat_payload = data[idat_offset + 8 : idat_offset + 8 + idat_len]
    raw = zlib.decompress(idat_payload)
    # Each row has 1 filter byte + 3 bytes per pixel
    assert len(raw) == 2 * (1 + 2 * 3)


def test_ppm_to_png_rejects_non_p6_magic(tmp_path):
    ppm_path = tmp_path / "bad.ppm"
    png_path = tmp_path / "out.png"
    ppm_path.write_bytes(b"P3\n2 2\n255\n")  # P3 is ASCII format, not binary

    with pytest.raises(ValueError, match="not a P6 PPM"):
        qemu_screendump._ppm_to_png(str(ppm_path), str(png_path))


def test_ppm_to_png_skips_comment_lines(tmp_path):
    ppm_path = tmp_path / "commented.ppm"
    png_path = tmp_path / "out.png"
    # PPM with a comment line after magic
    header = b"P6\n# This is a comment\n2 2\n255\n"
    pixels = bytes([255, 0, 0] * 4)
    ppm_path.write_bytes(header + pixels)

    qemu_screendump._ppm_to_png(str(ppm_path), str(png_path))

    data = png_path.read_bytes()
    assert data[:8] == b"\x89PNG\r\n\x1a\n"


# ---------------------------------------------------------------------------
# main() — argument handling
# ---------------------------------------------------------------------------

def test_main_exits_1_when_monitor_connect_fails(monkeypatch):
    monkeypatch.setattr(qemu_screendump, "_send_screendump",
                        lambda: (_ for _ in ()).throw(OSError("connection refused")))
    with pytest.raises(SystemExit) as exc_info:
        qemu_screendump.main()
    assert exc_info.value.code == 1


def test_main_exits_1_when_ppm_not_found(monkeypatch, tmp_path):
    monkeypatch.setattr(qemu_screendump, "_send_screendump", lambda: None)
    monkeypatch.setattr(qemu_screendump, "PPM_PATH", str(tmp_path / "nonexistent.ppm"))
    with pytest.raises(SystemExit) as exc_info:
        qemu_screendump.main()
    assert exc_info.value.code == 1


def test_main_converts_ppm_when_png_arg_given(monkeypatch, tmp_path):
    ppm_path = tmp_path / "frame.ppm"
    png_path = tmp_path / "out.png"
    ppm_path.write_bytes(_make_ppm(2, 2))

    monkeypatch.setattr(qemu_screendump, "_send_screendump", lambda: None)
    monkeypatch.setattr(qemu_screendump, "PPM_PATH", str(ppm_path))
    monkeypatch.setattr(qemu_screendump.sys, "argv", ["qemu_screendump.py", str(png_path)])

    qemu_screendump.main()  # should not raise

    assert png_path.exists()
    assert png_path.read_bytes()[:8] == b"\x89PNG\r\n\x1a\n"
