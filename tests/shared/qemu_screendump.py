"""Send a screendump command to the QEMU human monitor socket.

Writes the VGA framebuffer to /tmp/qemu-desktop.ppm on the GHA runner host.
Used as a fallback screenshot mechanism when in-VM methods (grim, gdbus)
are unavailable due to mutter running in software-rendering mode.
"""
import os
import socket
import sys
import time

SOCK_PATH = '/tmp/qemu-monitor.sock'
PPM_PATH = '/tmp/qemu-desktop.ppm'


def main():
    try:
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
        # File is written by QEMU (root); permissions are fixed by the caller.
        if os.path.exists(PPM_PATH):
            print('screendump size: ' + str(os.path.getsize(PPM_PATH)) + ' bytes', flush=True)
        else:
            print('WARNING: ' + PPM_PATH + ' not found after screendump', flush=True)
            sys.exit(1)
    except Exception as exc:
        print('QEMU monitor connect/send error: ' + str(exc), flush=True)
        sys.exit(1)


if __name__ == '__main__':
    main()
