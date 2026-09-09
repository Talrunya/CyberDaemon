from dataclasses import dataclass
from pathlib import Path
import re


VENDOR_ID = 0x1B1C
RECEIVER_PRODUCT_ID = 0x0A97

INPUT_INTERFACE = 3
VENDOR_INTERFACE = 4


@dataclass
class HIDInterface:
    path: str
    interface: int | None
    vendor_id: int
    product_id: int


class HS80HID:
    """Portable HS80 MAX HID discovery."""

    def __init__(self):
        self.interfaces: list[HIDInterface] = []

    def discover(self) -> list[HIDInterface]:
        self.interfaces.clear()

        for hidraw in sorted(Path("/sys/class/hidraw").glob("hidraw*")):
            uevent = hidraw / "device" / "uevent"

            if not uevent.exists():
                continue

            data = self._read_uevent(uevent)

            vendor, product = self._parse_hid_id(
                data.get("HID_ID")
            )

            if vendor != VENDOR_ID:
                continue

            if product != RECEIVER_PRODUCT_ID:
                continue

            interface = self._parse_interface(
                data.get("HID_PHYS")
            )

            self.interfaces.append(
                HIDInterface(
                    path=f"/dev/{hidraw.name}",
                    interface=interface,
                    vendor_id=vendor,
                    product_id=product,
                )
            )

        return self.interfaces

    def input_interface(self) -> HIDInterface | None:
        return self._find_interface(INPUT_INTERFACE)

    def vendor_interface(self) -> HIDInterface | None:
        return self._find_interface(VENDOR_INTERFACE)

    def _find_interface(
        self,
        interface_number: int,
    ) -> HIDInterface | None:

        for device in self.interfaces:
            if device.interface == interface_number:
                return device

        return None

    @staticmethod
    def _read_uevent(path: Path) -> dict[str, str]:
        result = {}

        try:
            for line in path.read_text(
                errors="ignore"
            ).splitlines():

                if "=" not in line:
                    continue

                key, value = line.split("=", 1)
                result[key] = value

        except OSError:
            pass

        return result

    @staticmethod
    def _parse_hid_id(
        value: str | None,
    ) -> tuple[int | None, int | None]:

        if not value:
            return None, None

        match = re.match(
            r"^[0-9A-Fa-f]+:([0-9A-Fa-f]{8}):([0-9A-Fa-f]{8})$",
            value,
        )

        if not match:
            return None, None

        try:
            vendor = int(match.group(1), 16)
            product = int(match.group(2), 16)

            return vendor, product

        except ValueError:
            return None, None

    @staticmethod
    def _parse_interface(
        value: str | None,
    ) -> int | None:

        if not value:
            return None

        match = re.search(r"/input(\d+)$", value)

        if not match:
            return None

        try:
            return int(match.group(1))

        except ValueError:
            return None