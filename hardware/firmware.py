from __future__ import annotations

import re
import webbrowser
from dataclasses import dataclass
from pathlib import Path
from typing import Any


CORSAIR_FIRMWARE_URL = "https://www.corsair.com/firmware-updater"

CORSAIR_API_URL = (
    "https://www.corsair.com/"
    "firmware-storage/firmware/public/"
)

HS80_MAX_RECEIVER_ID = (
    "hs80-max-wireless-receiver_1b1c_0a97"
)

# Version/package metadata confirmed from the Corsair Web Updater.
HS80_MAX_RECEIVER_FW_URL = (
    CORSAIR_API_URL
    + "fw/"
    + HS80_MAX_RECEIVER_ID
    + ".json"
)

# Device/Bragi capability profile.
HS80_MAX_RECEIVER_DEVICE_URL = (
    CORSAIR_API_URL
    + "manifests/"
    + HS80_MAX_RECEIVER_ID
    + "_manifest.json"
)

# Automatic update checks are intentionally infrequent.
AUTO_CHECK_INTERVAL_HOURS = 12
AUTO_CHECK_STATE_FILE = (
    Path.home()
    / ".config"
    / "CyberDaemon"
    / "firmware_check.json"
)


@dataclass
class FirmwareInfo:
    """Firmware information for one HS80 MAX component."""

    current: str | None = None
    latest: str | None = None
    update_available: bool = False
    status: str = "NOT CHECKED"
    error: str | None = None


class FirmwareManager:
    """
    Firmware/update coordinator for CyberDaemon.

    The manager deliberately does NOT flash firmware yet.
    It provides:
      - headset current firmware
      - receiver current firmware
      - version comparison helpers
      - safe access to Corsair's official web updater

    The real Corsair firmware download/flash protocol will be attached
    after the WebHID updater has been fully reverse-engineered.
    """

    def __init__(
        self,
        receiver=None,
        headset=None,
    ):
        self.receiver = receiver
        self.headset = headset

        self.headset_info = FirmwareInfo()
        self.receiver_info = FirmwareInfo()

        self._last_auto_check = self._load_last_auto_check()
        self._last_notified_headset_latest = None
        self._last_notified_receiver_latest = None

    def known_latest_versions(self):
        """Return the latest firmware versions advertised by Corsair."""

        return {
            "headset": None,
            "receiver": self.get_latest_receiver_firmware(),
        }

    # =========================================================
    # CORSAIR METADATA
    # =========================================================

    @staticmethod
    def _fetch_json(
        url: str,
        timeout: float = 8.0,
    ):
        """Fetch a public Corsair firmware JSON document."""

        import json
        from urllib.request import Request, urlopen

        request = Request(
            url,
            headers={
                "User-Agent": (
                    "CyberDaemon/1.0 "
                    "(HS80 MAX Firmware Check)"
                ),
                "Referer": (
                    "https://www.corsair.com/"
                    "firmware-updater/index.html"
                ),
                "Accept": "application/json",
            },
        )

        with urlopen(
            request,
            timeout=timeout,
        ) as response:
            return json.loads(
                response.read().decode("utf-8")
            )

    def get_latest_receiver_firmware(
        self,
    ) -> str | None:
        """Read the receiver latest version from Corsair's package JSON."""

        try:
            data = self._fetch_json(
                HS80_MAX_RECEIVER_FW_URL
            )

            package = (
                data
                .get("packages", {})
                .get("hs80_max_wireless_dongle")
            )

            if not isinstance(package, dict):
                raise ValueError(
                    "HS80 MAX receiver package missing "
                    "in Corsair firmware JSON."
                )

            version = (
                package
                .get("provides", {})
                .get("application")
            )

            if not isinstance(version, str):
                raise ValueError(
                    "Receiver application version missing "
                    "from Corsair firmware JSON."
                )

            version = version.strip()

            if self._parse_version(version) is None:
                raise ValueError(
                    f"Invalid receiver firmware version: {version}"
                )

            self.receiver_info.latest = version
            self.receiver_info.error = None
            self.receiver_info.status = "LATEST READ"

            return version

        except Exception as exc:
            self.receiver_info.error = str(exc)
            self.receiver_info.status = "LATEST READ FAILED"

            print(
                "[CyberDaemon Firmware] "
                "Receiver metadata read failed:",
                exc,
            )

            return None

    def get_receiver_package_metadata(
        self,
    ):
        """Return the receiver package metadata from Corsair."""

        try:
            data = self._fetch_json(
                HS80_MAX_RECEIVER_FW_URL
            )

            package = (
                data
                .get("packages", {})
                .get("hs80_max_wireless_dongle")
            )

            if not isinstance(package, dict):
                return None

            provides = package.get(
                "provides",
                {}
            )

            return {
                "version": provides.get(
                    "application"
                ),
                "release_date": package.get(
                    "release-date"
                ),
                "source": package.get(
                    "source"
                ),
                "integrity": package.get(
                    "integrity"
                ),
                "fw_config_url": (
                    HS80_MAX_RECEIVER_DEVICE_URL
                ),
            }

        except Exception as exc:
            print(
                "[CyberDaemon Firmware] "
                "Receiver package metadata failed:",
                exc,
            )
            return None

    # =========================================================
    # AUTOMATIC CHECK STATE
    # =========================================================

    @staticmethod
    def _load_last_auto_check():
        try:
            data = AUTO_CHECK_STATE_FILE.read_text(
                encoding="utf-8"
            )
            import json
            value = json.loads(data)
            return float(value.get("last_check", 0))
        except Exception:
            return 0.0

    def _save_last_auto_check(self, timestamp):
        try:
            AUTO_CHECK_STATE_FILE.parent.mkdir(
                parents=True,
                exist_ok=True,
            )
            import json
            AUTO_CHECK_STATE_FILE.write_text(
                json.dumps(
                    {"last_check": float(timestamp)}
                ),
                encoding="utf-8",
            )
        except Exception:
            # A failed local timestamp write must never affect headset control.
            pass

    def automatic_check_due(self, now=None) -> bool:
        """Return whether the 12-hour automatic firmware check is due."""

        import time

        if now is None:
            now = time.time()

        return (
            float(now) - self._last_auto_check
            >= AUTO_CHECK_INTERVAL_HOURS * 60 * 60
        )

    def mark_automatic_check(self, now=None):
        """Remember a successful automatic check attempt timestamp."""

        import time

        if now is None:
            now = time.time()

        self._last_auto_check = float(now)
        self._save_last_auto_check(now)

    def get_new_update_notifications(self):
        """Return one-time notifications for newly discovered versions."""

        notifications = []

        headset_latest = self.headset_info.latest
        if (
            headset_latest
            and headset_latest != self._last_notified_headset_latest
            and self.headset_info.update_available
        ):
            notifications.append(
                (
                    "HEADSET",
                    headset_latest,
                )
            )
            self._last_notified_headset_latest = headset_latest

        receiver_latest = self.receiver_info.latest
        if (
            receiver_latest
            and receiver_latest != self._last_notified_receiver_latest
            and self.receiver_info.update_available
        ):
            notifications.append(
                (
                    "WIRELESS RECEIVER",
                    receiver_latest,
                )
            )
            self._last_notified_receiver_latest = receiver_latest

        return notifications

    # =========================================================
    # VERSION HELPERS
    # =========================================================

    @staticmethod
    def _parse_version(
        value: str | None,
    ) -> tuple[int, int, int] | None:
        if not value:
            return None

        match = re.fullmatch(
            r"\s*(\d+)\.(\d+)\.(\d+)\s*",
            str(value),
        )

        if not match:
            return None

        return tuple(
            int(part)
            for part in match.groups()
        )

    @classmethod
    def compare_versions(
        cls,
        current: str | None,
        latest: str | None,
    ) -> int | None:
        """
        Compare two semantic firmware versions.

        Returns:
            -1 current < latest
             0 current == latest
             1 current > latest
            None when either version is invalid/missing.
        """

        current_version = cls._parse_version(
            current
        )
        latest_version = cls._parse_version(
            latest
        )

        if (
            current_version is None
            or latest_version is None
        ):
            return None

        if current_version < latest_version:
            return -1

        if current_version > latest_version:
            return 1

        return 0

    # =========================================================
    # CURRENT VERSIONS
    # =========================================================

    def read_headset_version(self) -> str | None:
        """Read the already-supported HS80 MAX headset firmware."""

        if self.headset is None:
            self.headset_info.error = (
                "HS80 headset is not connected."
            )
            return None

        try:
            version = self.headset.get_firmware()

        except Exception as exc:
            self.headset_info.error = str(exc)
            self.headset_info.status = "READ FAILED"
            return None

        if version:
            self.headset_info.current = str(version)
            self.headset_info.status = "CURRENT READ"

        return self.headset_info.current

    def read_receiver_version(self) -> str | None:
        """
        Read receiver firmware.

        receiver.read_firmware() is already present in the project.
        Its response format is intentionally parsed conservatively here;
        no guessed receiver version is written into the UI.
        """

        if self.receiver is None:
            self.receiver_info.error = (
                "Wireless receiver is not connected."
            )
            return None

        try:
            response = self.receiver.read_firmware()

        except Exception as exc:
            self.receiver_info.error = str(exc)
            self.receiver_info.status = "READ FAILED"
            return None

        version = self._parse_receiver_response(
            response
        )

        if version:
            self.receiver_info.current = version
            self.receiver_info.status = "CURRENT READ"
        else:
            self.receiver_info.status = "NOT AVAILABLE"

        return self.receiver_info.current

    @staticmethod
    def _parse_receiver_response(
        response: bytes | None,
    ) -> str | None:
        """
        Parse a receiver firmware response only when its structure is known.

        We currently do not have a confirmed HS80 MAX receiver response
        layout, so this method intentionally returns None instead of
        inventing a version from arbitrary HID bytes.
        """

        if not response:
            return None

        # Kept as the single isolated parser so the real receiver response
        # format can be added after we capture/confirm it from Corsair.
        return None

    def read_current_versions(self):
        """Read both components without performing any update."""

        return {
            "headset": self.read_headset_version(),
            "receiver": self.read_receiver_version(),
        }

    # =========================================================
    # UPDATE CHECK
    # =========================================================

    def check_for_updates(
        self,
        headset_latest: str | None = None,
        receiver_latest: str | None = None,
    ):
        """
        Compare known latest-version metadata with current versions.

        The latest-version values are optional until the Corsair metadata
        endpoint is identified. This keeps the UI functional without
        pretending a guessed endpoint is authoritative.
        """

        if headset_latest:
            self.headset_info.latest = str(
                headset_latest
            )

        if receiver_latest:
            self.receiver_info.latest = str(
                receiver_latest
            )
        else:
            receiver_latest = (
                self.get_latest_receiver_firmware()
            )
            if receiver_latest:
                self.receiver_info.latest = (
                    receiver_latest
                )

        self._update_state(
            self.headset_info
        )
        self._update_state(
            self.receiver_info
        )

        self.mark_automatic_check()

        return (
            self.headset_info,
            self.receiver_info,
        )

    def _update_state(
        self,
        info: FirmwareInfo,
    ):
        if not info.current:
            return

        if not info.latest:
            info.status = "CHECK REQUIRED"
            info.update_available = False
            return

        comparison = self.compare_versions(
            info.current,
            info.latest,
        )

        if comparison is None:
            info.status = "VERSION UNKNOWN"
            info.update_available = False
            return

        if comparison < 0:
            info.status = "UPDATE AVAILABLE"
            info.update_available = True

        elif comparison == 0:
            info.status = "UP TO DATE"
            info.update_available = False

        else:
            info.status = "CURRENT VERSION IS NEWER"
            info.update_available = False

    # =========================================================
    # OFFICIAL UPDATER
    # =========================================================

    @staticmethod
    def open_official_updater() -> bool:
        """Open Corsair's official firmware updater in the browser."""

        try:
            return bool(
                webbrowser.open(
                    CORSAIR_FIRMWARE_URL
                )
            )
        except Exception:
            return False

    # =========================================================
    # FLASH PLACEHOLDERS
    # =========================================================

    def update_headset(
        self,
        latest_version: str,
    ) -> tuple[bool, str]:
        """
        Firmware flashing is deliberately not implemented yet.

        Returns a controlled result so the Settings UI can report the
        state without sending unsafe/guessed firmware commands.
        """

        del latest_version

        return (
            False,
            "Firmware flashing is not implemented yet.",
        )

    def update_receiver(
        self,
        latest_version: str,
    ) -> tuple[bool, str]:
        """Controlled placeholder for the future receiver flasher."""

        del latest_version

        return (
            False,
            "Receiver firmware flashing is not implemented yet.",
        )
