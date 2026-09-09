from dataclasses import dataclass

from .receiver import HS80Receiver


HEADSET_ENDPOINT = bytes([0x09])

CMD_GET_FIRMWARE = bytes([0x02, 0x13])
CMD_GET_BATTERY = bytes([0x02, 0x0F])
CMD_GET_MICROPHONE = bytes([0x02, 0xA6])

CMD_OPEN_RGB_ENDPOINT = bytes([0x0D, 0x00, 0x22])
CMD_WRITE_RGB = bytes([0x06, 0x00])

CMD_SIDETONE_MODE = bytes([0x01, 0x46, 0x00])
CMD_SIDETONE = bytes([0x01, 0x47, 0x00])

CMD_SLEEP_MODE = bytes([0x01, 0x0D, 0x00])
CMD_SLEEP = bytes([0x01, 0x0E, 0x00])

RGB_DATA_TYPE = bytes([0x12, 0x00])


@dataclass
class HeadsetStatus:
    battery: int | None = None
    microphone_muted: bool | None = None
    firmware: str | None = None


class HS80Headset:
    def __init__(self, receiver):
        self.receiver = receiver
        self.status = HeadsetStatus()

        # Battery values from the HS80 MAX can occasionally be corrupted by
        # stale/asynchronous HID reports. Only accept a new value after
        # three identical valid readings.
        self._battery_valid_count = 0
        self._battery_pending = None

    def get_firmware(self):
        response = self.receiver.transfer(
            HEADSET_ENDPOINT,
            CMD_GET_FIRMWARE,
        )

        if response is None or len(response) < 8:
            return self.status.firmware

        # The known HS80 MAX firmware response has the vendor response
        # identifier at byte 2 and 00 at byte 3:
        #
        #   01 01 02 00 00 16 0f 01 ...
        #
        # Other asynchronous reports can also start with 01 01 02 00,
        # but they do not carry the firmware signature byte at index 7.
        if response[2] != 0x02 or response[3] != 0x00 or response[7] != 0x01:
            print(
                "[HS80] Invalid firmware response "
                "(not a firmware packet; keeping previous value)."
            )
            return self.status.firmware

        major = response[4]
        minor = response[5]
        patch = response[6]

        # Firmware components must be plausible version numbers.
        # This prevents asynchronous/status data such as 118.2.0
        # from being displayed as firmware.
        if major > 9 or minor > 99 or patch > 99:
            print(
                "[HS80] Invalid firmware values: "
                f"{major}.{minor}.{patch} "
                "(keeping previous value)."
            )
            return self.status.firmware

        firmware = f"{major}.{minor}.{patch}"

        # Do not allow the all-zero value to replace a known good version.
        if firmware == "0.0.0":
            print(
                "[HS80] Invalid firmware response: 0.0.0 "
                "(keeping previous value)."
            )
            return self.status.firmware

        self.status.firmware = firmware
        return firmware

    def get_battery(self):
        response = self.receiver.transfer(
            HEADSET_ENDPOINT,
            CMD_GET_BATTERY,
        )

        if response is None or len(response) < 6:
            return self.status.battery

        # A valid battery packet uses response identifier 0x02.
        # The receiver can otherwise hand us a stale response from another
        # command (for example an RGB response with identifier 0x06).
        if response[2] != 0x02 or response[3] != 0x00:
            print(
                "[HS80] Invalid battery packet "
                f"(response id 0x{response[2]:02x}; keeping previous value)."
            )
            return self.status.battery

        raw = response[4] | (response[5] << 8)

        # HS80 MAX occasionally returns zero/stale data.
        # Never overwrite the last valid value with 0.
        if raw == 0:
            print(
                "[HS80] Battery response is 0 "
                "(keeping previous value)."
            )

            self._battery_valid_count = 0
            self._battery_pending = None

            return self.status.battery

        # Battery is represented as value * 10.
        # Anything above 1000 would be outside the valid 0..100% range
        # and is therefore a corrupted/non-battery response.
        if raw > 1000:
            print(
                "[HS80] Invalid battery raw value:",
                raw,
                "(keeping previous value).",
            )

            self._battery_valid_count = 0
            self._battery_pending = None

            return self.status.battery

        battery = min(
            100,
            max(0, raw // 10),
        )

        # Require THREE IDENTICAL valid readings.
        # The previous implementation counted three readings even when they
        # were different (e.g. 63 -> 100 -> 63), which still allowed glitches.
        if battery != self._battery_pending:
            self._battery_pending = battery
            self._battery_valid_count = 1
            return self.status.battery

        self._battery_valid_count += 1

        if self._battery_valid_count < 3:
            return self.status.battery

        self.status.battery = battery

        self._battery_valid_count = 0
        self._battery_pending = None

        return self.status.battery

    def get_microphone_status(self):
        response = self.receiver.transfer(
            HEADSET_ENDPOINT,
            CMD_GET_MICROPHONE,
        )

        if response is None or len(response) < 5:
            return None

        muted = response[4] != 0

        self.status.microphone_muted = muted

        return muted

    def initialize_rgb(self):
        response = self.receiver.transfer(
            HEADSET_ENDPOINT,
            CMD_OPEN_RGB_ENDPOINT,
        )

        if response is None:
            print("[HS80 RGB] Failed to open RGB endpoint.")
            return False

        print(
            "[HS80 RGB] RGB endpoint opened: "
            + response[:8].hex(" ")
        )

        return True

    def set_rgb_static(
        self,
        red: int,
        green: int,
        blue: int,
        brightness: int = 100,
    ):
        """
        Set both HS80 MAX RGB zones to one static color.

        OpenLinkHub uses an 8-byte color packet:
            zone 1: R G B
            zone 2: R G B
            remaining bytes: 0

        The RGB command payload contains:
            length = 8
            data type = 12 00
            color data = 8 bytes
        """

        red = max(0, min(255, int(red)))
        green = max(0, min(255, int(green)))
        blue = max(0, min(255, int(blue)))

        brightness = max(0, min(100, int(brightness)))

        scale = brightness / 100.0

        red = int(red * scale)
        green = int(green * scale)
        blue = int(blue * scale)

        # Two RGB zones.
        color_data = bytes([
            red,
            green,
            blue,

            red,
            green,
            blue,

            0x00,
            0x00,
        ])

        # OpenLinkHub:
        #   uint16 length
        #   2 bytes padding/header
        #   12 00 data type
        #   8 bytes color data
        payload = bytearray()

        payload += bytes([0x08, 0x00])
        payload += bytes([0x00, 0x00])
        payload += RGB_DATA_TYPE
        payload += color_data

        command = CMD_WRITE_RGB + bytes(payload)

        response = self.receiver.transfer(
            HEADSET_ENDPOINT,
            command,
        )

        if response is None:
            print("[HS80 RGB] RGB write failed.")
            return False

        return True

    def set_sidetone(self, percent: int) -> bool:
        """Set HS80 MAX hardware sidetone level."""

        percent = max(0, min(100, int(percent)))

        if percent == 0:
            # Sidetone OFF
            response = self.receiver.transfer(
                HEADSET_ENDPOINT,
                CMD_SIDETONE_MODE + bytes([0x01]),
            )

            return response is not None

        # Sidetone ON
        response = self.receiver.transfer(
            HEADSET_ENDPOINT,
            CMD_SIDETONE_MODE + bytes([0x00]),
        )

        if response is None:
            return False

        # HS80 MAX: value = percent * 10, uint16 little-endian
        value = percent * 10

        response = self.receiver.transfer(
            HEADSET_ENDPOINT,
            CMD_SIDETONE + value.to_bytes(2, "little"),
        )

        return response is not None

    def set_sleep_timer(self, minutes: int) -> bool:
        """Set HS80 MAX automatic power-off timer."""

        allowed = (0, 1, 5, 10, 15, 30, 60)

        minutes = int(minutes)

        if minutes not in allowed:
            print(
                f"[HS80 SLEEP] Unsupported timer: {minutes} min"
            )
            return False

        if minutes == 0:
            # Disable automatic power-off.
            response = self.receiver.transfer(
                HEADSET_ENDPOINT,
                CMD_SLEEP_MODE + bytes([0x00]),
            )

            if response is None:
                print(
                    "[HS80 SLEEP] Failed to disable "
                    "automatic power-off."
                )
                return False

            print(
                "[HS80 SLEEP] Auto power-off disabled."
            )

            return True

        # Enable automatic power-off.
        response = self.receiver.transfer(
            HEADSET_ENDPOINT,
            CMD_SLEEP_MODE + bytes([0x01]),
        )

        if response is None:
            print(
                "[HS80 SLEEP] Failed to enable "
                "automatic power-off."
            )
            return False

        # HS80 MAX expects the timeout in milliseconds
        # as uint32 little-endian.
        milliseconds = minutes * 60 * 1000

        response = self.receiver.transfer(
            HEADSET_ENDPOINT,
            CMD_SLEEP + milliseconds.to_bytes(
                4,
                "little",
            ),
        )

        if response is None:
            print(
                "[HS80 SLEEP] Failed to set timer:"
                f" {minutes} min"
            )
            return False

        print(
            "[HS80 SLEEP] Auto power-off set to:"
            f" {minutes} min"
        )

        return True

    def read_status(
        self,
        include_firmware: bool = False,
        include_microphone: bool = True,
    ):
        # IMPORTANT:
        # The previous code read firmware on every status poll even when
        # include_firmware=False. That created unnecessary HID traffic and
        # allowed unrelated/stale reports to be interpreted as firmware.
        if include_firmware:
            self.get_firmware()

        self.get_battery()

        if include_microphone:
            self.get_microphone_status()

        return self.status
