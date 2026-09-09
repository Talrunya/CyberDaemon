from dataclasses import dataclass

from .hid import HS80HID, HIDInterface


BUFFER_SIZE = 64
WRITE_SIZE = 65
READ_TIMEOUT_MS = 1000
LISTENER_TIMEOUT_MS = 100

# HS80 MAX initialization commands
CMD_SOFTWARE_MODE = bytes([0x01, 0x03, 0x00, 0x02])
CMD_OPEN_WRITE_ENDPOINT = bytes([0x0D, 0x01, 0x02])

# Vendor endpoint used by the HS80 MAX receiver/headset
HEADSET_ENDPOINT = bytes([0x09])


@dataclass
class ReceiverStatus:
    connected: bool = False
    path: str | None = None
    interface: int | None = None


class HS80Receiver:
    """Communication layer for the HS80 MAX wireless receiver."""

    def __init__(self, hid: HS80HID | None = None):
        self.hid = hid or HS80HID()
        self.interface: HIDInterface | None = None
        self.status = ReceiverStatus()

        # Normal command/response handle.
        self.device = None

        # Separate asynchronous event handle.
        self.listener = None

    def connect(self) -> bool:
        """Discover and open the HS80 MAX vendor HID interface."""
        self.hid.discover()
        self.interface = self.hid.vendor_interface()

        if self.interface is None:
            self.status = ReceiverStatus()
            return False

        try:
            import hid

            self.device = hid.device()
            self.device.open_path(self.interface.path.encode())
            self.device.set_nonblocking(False)

            # Open a second handle for asynchronous reports.  It must point
            # to the same physical HID interface, but it is a separate handle
            # so normal command responses are not consumed by the listener.
            self.listener = hid.device()
            self.listener.open_path(self.interface.path.encode())
            self.listener.set_nonblocking(False)

        except Exception as exc:
            print(f"[HS80] HID open failed: {exc}")

            if self.listener is not None:
                try:
                    self.listener.close()
                except Exception:
                    pass

            if self.device is not None:
                try:
                    self.device.close()
                except Exception:
                    pass

            self.listener = None
            self.device = None
            self.interface = None
            self.status = ReceiverStatus()
            return False

        self.status = ReceiverStatus(
            connected=True,
            path=self.interface.path,
            interface=self.interface.interface,
        )

        print(
            f"[HS80] Connected: {self.status.path} "
            f"(interface {self.status.interface})"
        )

        return True

    def initialize(self) -> bool:
        """Initialize HS80 MAX software/write communication mode."""
        if self.device is None or not self.connected:
            print("[HS80] Initialize failed: receiver not connected.")
            return False

        print("[HS80] Initializing HS80 MAX...")

        response = self.transfer(
            HEADSET_ENDPOINT,
            CMD_SOFTWARE_MODE,
        )

        if response is None:
            print("[HS80] Software mode: no response.")
            return False

        print(
            "[HS80] Software mode response:",
            response[:8].hex(" "),
        )

        response = self.transfer(
            HEADSET_ENDPOINT,
            CMD_OPEN_WRITE_ENDPOINT,
        )

        if response is None:
            print("[HS80] Open write endpoint: no response.")
            return False

        print(
            "[HS80] Open write endpoint response:",
            response[:8].hex(" "),
        )

        print("[HS80] Initialization complete.")
        return True

    def disconnect(self) -> None:
        """Close all HID handles."""
        if self.listener is not None:
            try:
                self.listener.close()
            except Exception:
                pass

        if self.device is not None:
            try:
                self.device.close()
            except Exception:
                pass

        self.listener = None
        self.device = None
        self.interface = None
        self.status = ReceiverStatus()

    @property
    def connected(self) -> bool:
        return self.status.connected

    @property
    def path(self) -> str | None:
        return self.status.path

    @property
    def interface_number(self) -> int | None:
        return self.status.interface

    def read_listener(self) -> bytes | None:
        """Read one asynchronous report without blocking the worker loop."""
        if self.listener is None or not self.connected:
            return None

        try:
            response = self.listener.read(
                BUFFER_SIZE,
                LISTENER_TIMEOUT_MS,
            )

            if not response:
                return None

            data = bytes(response)

            #print(
                #"[HS80 DEBUG] LISTENER:",
                #data.hex(" "),
            #)

            return data

        except Exception as exc:
            print(f"[HS80] Listener read failed: {exc}")
            return None

    def read_firmware(self) -> bytes | None:
        """Read the HS80 MAX firmware response."""
        return self.transfer(
            HEADSET_ENDPOINT,
            bytes([0x02, 0x13]),
        )

    def transfer(
        self,
        endpoint: bytes,
        command: bytes,
    ) -> bytes | None:
        """Send one raw HS80 MAX vendor command and return its response."""
        if self.device is None or not self.connected:
            return None

        if not endpoint:
            print("[HS80] HID transfer failed: empty endpoint.")
            return None

        if len(command) > WRITE_SIZE - 3:
            print(
                "[HS80] HID transfer failed: command too large "
                f"({len(command)} bytes)."
            )
            return None

        report = bytearray(WRITE_SIZE)
        report[0] = 0x00
        report[1] = 0x02
        report[2] = endpoint[0]
        report[3:3 + len(command)] = command

        try:
            #print(
                #"[HS80 DEBUG] HID OUT:",
                #report.hex(" "),
            #)

            written = self.device.write(report)
            if written <= 0:
                print("[HS80] HID write failed.")
                return None

            response = self.device.read(
                BUFFER_SIZE,
                READ_TIMEOUT_MS,
            )

            if not response:
                print("[HS80 DEBUG] HID IN: <no data>")
                return None

            data = bytes(response)

            #print(
                #"[HS80 DEBUG] HID IN:",
                #data.hex(" "),
            #)

            return data

        except Exception as exc:
            print(f"[HS80] HID transfer failed: {exc}")
            return None

