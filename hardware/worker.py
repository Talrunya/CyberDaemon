from __future__ import annotations

import colorsys
import math
import subprocess
import time
from queue import Empty, Queue

import hid

from PySide6.QtCore import QThread, Signal

from .hid import HS80HID
from .receiver import HS80Receiver
from .headset import HS80Headset


class HardwareWorker(QThread):
    """Background worker for HS80 MAX hardware, RGB and volume."""

    status_updated = Signal(object)
    listener_data = Signal(object)
    connection_changed = Signal(bool)
    error = Signal(str)
    volume_changed = Signal(int)

    EFFECT_FRAME_MS = 40
    PRESENCE_CHECK_MS = 1000
    PRESENCE_FAIL_LIMIT = 2

    def __init__(self, parent=None):
        super().__init__(parent)

        self.receiver = HS80Receiver()
        self.headset: HS80Headset | None = None

        self._input_device = None
        self._input_path = None

        self._running = True
        self._commands = Queue()

        self._headset_online = False
        self._presence_failures = 0
        self._last_presence_check = 0.0

        self._rgb_state = {
            "red": 0,
            "green": 255,
            "blue": 255,
            "brightness": 100,
            "effect": "Static",
        }

        self._effect_started = time.monotonic()

    # =========================================================
    # COMMAND API
    # =========================================================

    def apply_rgb(
        self,
        red,
        green,
        blue,
        brightness=100,
        effect="Static",
    ):
        """Queue a complete RGB state for execution in the worker thread."""
        self._commands.put(
            (
                "rgb",
                int(red),
                int(green),
                int(blue),
                int(brightness),
                str(effect),
            )
        )

    def set_volume(self, value):
        """Set the Linux default output volume to 0..100."""
        self._commands.put(("volume", int(value)))
    def set_sidetone(self, value):
        """Queue HS80 MAX hardware sidetone level."""
        self._commands.put(("sidetone", int(value)))
    def set_sleep_timer(self, minutes):
        """Queue HS80 MAX automatic power-off timer."""
        self._commands.put(("sleep_timer", int(minutes)))    
    # =========================================================
    # COMMAND PROCESSING
    # =========================================================

    def _process_commands(self):
        while True:
            try:
                command = self._commands.get_nowait()
            except Empty:
                return

            if not command:
                continue

            if command[0] == "rgb":
                (
                    _,
                    red,
                    green,
                    blue,
                    brightness,
                    effect,
                ) = command

                self._rgb_state = {
                    "red": max(0, min(255, red)),
                    "green": max(0, min(255, green)),
                    "blue": max(0, min(255, blue)),
                    "brightness": max(0, min(100, brightness)),
                    "effect": effect,
                }

                self._effect_started = time.monotonic()

                print(
                    "[HS80 RGB] STATE:",
                    f"R={self._rgb_state['red']}",
                    f"G={self._rgb_state['green']}",
                    f"B={self._rgb_state['blue']}",
                    f"Brightness={self._rgb_state['brightness']}",
                    f"Effect={self._rgb_state['effect']}",
                )

                if self._headset_online:
                    self._render_rgb_frame(force=True)

            elif command[0] == "volume":
                self._set_system_volume(command[1])

            elif command[0] == "sidetone":
                value = max(0, min(100, int(command[1])))

                if self.headset is None or not self._headset_online:
                    print(
                        "[HS80 SIDETONE] Cannot apply: "
                        "headset not connected."
                    )
                    continue

                success = self.headset.set_sidetone(value)

                if success:
                    print(
                        f"[HS80 SIDETONE] Hardware level: {value}%"
                    )
                else:
                    print(
                        f"[HS80 SIDETONE] Hardware apply failed: {value}%"
                    )
            elif command[0] == "sleep_timer":
                minutes = int(command[1])

                if self.headset is None or not self._headset_online:
                    print(
                        "[HS80 SLEEP] Cannot apply: "
                        "headset not connected."
                    )
                    continue

                success = self.headset.set_sleep_timer(minutes)

                if success:
                    print(
                        f"[HS80 SLEEP] Auto power-off: "
                        f"{minutes} min"
                    )
                else:
                    print(
                        f"[HS80 SLEEP] Hardware apply failed: "
                        f"{minutes} min"
                    )
    # =========================================================
    # SYSTEM VOLUME
    # =========================================================

    @staticmethod
    def _set_system_volume(value):
        value = max(0, min(100, int(value)))

        # PipeWire / WirePlumber
        try:
            result = subprocess.run(
                [
                    "wpctl",
                    "set-volume",
                    "@DEFAULT_AUDIO_SINK@",
                    f"{value}%",
                ],
                capture_output=True,
                text=True,
                timeout=1.0,
                check=False,
            )

            if result.returncode == 0:
                print(f"[HS80 AUDIO] System volume: {value}%")
                return value

        except (
            FileNotFoundError,
            subprocess.SubprocessError,
        ):
            pass

        # PulseAudio compatibility
        try:
            result = subprocess.run(
                [
                    "pactl",
                    "set-sink-volume",
                    "@DEFAULT_SINK@",
                    f"{value}%",
                ],
                capture_output=True,
                text=True,
                timeout=1.0,
                check=False,
            )

            if result.returncode == 0:
                print(f"[HS80 AUDIO] System volume: {value}%")
                return value

        except (
            FileNotFoundError,
            subprocess.SubprocessError,
        ):
            pass

        print("[HS80 AUDIO] Failed to set system volume.")
        return None

    @staticmethod
    def _change_system_volume(delta):
        """Change the default Linux output volume by a relative amount."""

        delta = int(delta)

        try:
            result = subprocess.run(
                [
                    "wpctl",
                    "set-volume",
                    "@DEFAULT_AUDIO_SINK@",
                    f"{abs(delta)}%{"+" if delta >= 0 else "-"}",
                ],
                capture_output=True,
                text=True,
                timeout=1.0,
                check=False,
            )

            if result.returncode == 0:
                print(
                    "[HS80 AUDIO] Volume wheel:",
                    f"{abs(delta)}%{"+" if delta >= 0 else "-"}",
                )
                return True

        except (
            FileNotFoundError,
            subprocess.SubprocessError,
        ):
            pass

        try:
            result = subprocess.run(
                [
                    "pactl",
                    "set-sink-volume",
                    "@DEFAULT_SINK@",
                    f"{abs(delta)}%{"+" if delta >= 0 else "-"}",
                ],
                capture_output=True,
                text=True,
                timeout=1.0,
                check=False,
            )

            if result.returncode == 0:
                print(
                    "[HS80 AUDIO] Volume wheel:",
                    f"{abs(delta)}%{"+" if delta >= 0 else "-"}",
                )
                return True

        except (
            FileNotFoundError,
            subprocess.SubprocessError,
        ):
            pass

        return False

    # =========================================================
    # INPUT INTERFACE
    # =========================================================

    def _open_input_interface(self):
        """Open the HS80 MAX consumer-control HID interface dynamically."""

        try:
            hid_api = HS80HID()
            hid_api.discover()
            interface = hid_api.input_interface()

            if interface is None:
                print("[HS80 AUDIO] Input HID interface not found.")
                return False

            device = hid.device()
            device.open_path(interface.path.encode())
            device.set_nonblocking(True)

            self._input_device = device
            self._input_path = interface.path

            print(
                "[HS80 AUDIO] Input interface:",
                interface.path,
                f"(interface {interface.interface})",
            )
            return True

        except Exception as exc:
            print(
                f"[HS80 AUDIO] Input HID open failed: {exc}"
            )
            self._input_device = None
            self._input_path = None
            return False

    def _close_input_interface(self):
        if self._input_device is not None:
            try:
                self._input_device.close()
            except Exception:
                pass

        self._input_device = None
        self._input_path = None

    def _read_input_events(self):
        """Read consumer-control events without blocking the worker."""

        if self._input_device is None:
            return

        try:
            while True:
                data = self._input_device.read(64)

                if not data:
                    return

                packet = bytes(data)

                # HS80 MAX volume wheel reports observed on
                # the Consumer Control interface:
                #
                #   0c 01 ... = volume increment
                #   0c 02 ... = volume decrement
                #
                if len(packet) >= 2 and packet[0] == 0x0C:
                    if packet[1] == 0x01:
                        if self._change_system_volume(+5):
                            self._emit_current_volume()

                    elif packet[1] == 0x02:
                        if self._change_system_volume(-5):
                            self._emit_current_volume()

        except Exception as exc:
            print(
                f"[HS80 AUDIO] Input read failed: {exc}"
            )

    @staticmethod
    def _get_current_volume():
        """Read current Linux default output volume as 0..100."""

        try:
            result = subprocess.run(
                [
                    "wpctl",
                    "get-volume",
                    "@DEFAULT_AUDIO_SINK@",
                ],
                capture_output=True,
                text=True,
                timeout=1.0,
                check=False,
            )

            if result.returncode == 0:
                parts = result.stdout.strip().split()

                if parts:
                    value = float(parts[1])
                    return max(
                        0,
                        min(100, round(value * 100)),
                    )

        except (
            FileNotFoundError,
            ValueError,
            IndexError,
            subprocess.SubprocessError,
        ):
            pass

        return None

    def _emit_current_volume(self):
        value = self._get_current_volume()

        if value is not None:
            self.volume_changed.emit(value)

    # =========================================================
    # HEADSET PRESENCE
    # =========================================================

    def _probe_headset(self):
        """Check whether the powered headset answers through the receiver."""

        if self.headset is None:
            return False

        try:
            battery = self.headset.get_battery()
            return battery is not None
        except Exception as exc:
            print(
                f"[HS80] Headset presence check failed: {exc}"
            )
            return False

    def _set_headset_online(self):
        if self._headset_online:
            return

        self._headset_online = True
        self._presence_failures = 0

        print("[HS80] Headset ONLINE.")
        self.connection_changed.emit(True)

        if self.headset is not None:
            try:
                self.headset.initialize_rgb()

            except Exception as exc:
                print(
                    f"[HS80 RGB] Reinitialize failed: {exc}"
                )

            try:
                status = self.headset.read_status(
                    include_firmware=True
                )

                self.status_updated.emit(status)
            except Exception as exc:
                print(
                    f"[HS80] Online status read failed: {exc}"
                )

    def _set_headset_offline(self):
        if not self._headset_online:
            return

        self._headset_online = False
        self._presence_failures = 0

        print("[HS80] Headset OFFLINE.")
        self.connection_changed.emit(False)

    def _check_headset_presence(self):
        now = time.monotonic()

        if (
            now - self._last_presence_check
            < self.PRESENCE_CHECK_MS / 1000.0
        ):
            return

        self._last_presence_check = now

        online = self._probe_headset()

        if online:
            self._presence_failures = 0

            if not self._headset_online:
                self._set_headset_online()

        else:
            self._presence_failures += 1

            if (
                self._headset_online
                and self._presence_failures
                >= self.PRESENCE_FAIL_LIMIT
            ):
                self._set_headset_offline()

    # =========================================================
    # RGB EFFECT ENGINE
    # =========================================================

    def _render_rgb_frame(self, force=False):
        if self.headset is None or not self._headset_online:
            return

        state = self._rgb_state
        effect = state["effect"]

        elapsed = time.monotonic() - self._effect_started

        red = state["red"]
        green = state["green"]
        blue = state["blue"]

        if effect == "Static":
            pass

        elif effect == "Breathing":
            phase = (elapsed % 3.0) / 3.0
            wave = (
                math.sin(
                    phase * math.tau - math.pi / 2
                ) + 1.0
            ) / 2.0

            level = 0.08 + (0.92 * wave)

            red = int(red * level)
            green = int(green * level)
            blue = int(blue * level)

        elif effect == "Color Pulse":
            phase = (elapsed % 2.0) / 2.0
            level = (
                math.sin(
                    phase * math.tau
                ) + 1.0
            ) / 2.0

            level = 0.15 + (0.85 * level)

            red = int(red * level)
            green = int(green * level)
            blue = int(blue * level)

        elif effect == "Color Shift":
            hue = (elapsed / 6.0) % 1.0
            red, green, blue = self._hsv_rgb(
                hue,
                1.0,
                1.0,
            )

        elif effect == "Rainbow":
            hue = (elapsed / 5.0) % 1.0
            red, green, blue = self._hsv_rgb(
                hue,
                1.0,
                1.0,
            )

        elif effect == "Watercolor":
            hue = (
                0.5
                + 0.15
                * math.sin(
                    elapsed / 4.0
                    * math.tau
                )
            ) % 1.0

            red, green, blue = self._hsv_rgb(
                hue,
                0.45,
                1.0,
            )

        elif effect == "Spiral":
            hue = (elapsed / 5.0) % 1.0

            red, green, blue = self._hsv_rgb(
                hue,
                1.0,
                1.0,
            )

        else:
            print(
                "[HS80 RGB] Unsupported effect:",
                effect,
            )
            return

        success = self.headset.set_rgb_static(
            red,
            green,
            blue,
            state["brightness"],
        )

        if force or not success:
            if success:
                print(
                    "[HS80 RGB] Frame applied:",
                    effect,
                )
            else:
                print(
                    "[HS80 RGB] Frame apply failed:",
                    effect,
                )

    @staticmethod
    def _hsv_rgb(hue, saturation, value):
        red, green, blue = colorsys.hsv_to_rgb(
            hue % 1.0,
            max(0.0, min(1.0, saturation)),
            max(0.0, min(1.0, value)),
        )

        return (
            int(red * 255),
            int(green * 255),
            int(blue * 255),
        )

    # =========================================================
    # WORKER
    # =========================================================

    def run(self):
        """Connect and run hardware, RGB and audio processing."""

        try:
            if not self.receiver.connect():
                self.connection_changed.emit(False)
                return

            initialized = self.receiver.initialize()

            if not initialized:
                print(
                    "[HS80] Receiver initialization "
                    "did not complete."
                )

            self.headset = HS80Headset(
                self.receiver
            )

            self._open_input_interface()

            # The USB receiver can exist while the headset is switched off.
            # Only report CONNECTED when the headset itself answers.
            if self._probe_headset():
                self._set_headset_online()
            else:
                self._headset_online = False
                self.connection_changed.emit(False)
                print("[HS80] Receiver present, headset OFF.")

            poll_counter = 0
            last_rgb_frame = 0.0

            while self._running:

                # -------------------------------------------------
                # GUI commands
                # -------------------------------------------------

                self._process_commands()

                # -------------------------------------------------
                # Consumer Control / volume wheel
                # -------------------------------------------------

                self._read_input_events()

                # -------------------------------------------------
                # Headset power/presence
                # -------------------------------------------------

                self._check_headset_presence()

                # -------------------------------------------------
                # RGB animation
                # -------------------------------------------------

                now = time.monotonic()

                if (
                    self._headset_online
                    and self._rgb_state["effect"] != "Static"
                    and (
                        now - last_rgb_frame
                        >= self.EFFECT_FRAME_MS / 1000.0
                    )
                ):
                    self._render_rgb_frame()
                    last_rgb_frame = now

                # -------------------------------------------------
                # Vendor listener
                # -------------------------------------------------

                data = self.receiver.read_listener()

                if data:
                    self.listener_data.emit(data)

                    # Mic boom status
                    if (
                        len(data) >= 6
                        and data[0] == 0x03
                        and data[1] == 0x01
                        and data[2] == 0x01
                        and data[3] == 0xA6
                    ):
                        muted = data[5] != 0

                        self.headset.status.microphone_muted = (
                            muted
                        )

                        print(
                            "[HS80] Microphone:",
                            "MUTED"
                            if muted
                            else "ACTIVE",
                        )

                        self.status_updated.emit(
                            self.headset.status
                        )

                # -------------------------------------------------
                # Status polling every ~3 seconds
                # -------------------------------------------------

                if (
                    self._headset_online
                    and poll_counter <= 0
                ):
                    try:
                        status = self.headset.read_status(
                            include_firmware=False,
                            include_microphone=False,
                        )

                        self.status_updated.emit(status)

                    except Exception as exc:
                        print(
                            f"[HS80] Status read failed: {exc}"
                        )

                    poll_counter = 30

                poll_counter -= 1

                self.msleep(20)

        except Exception as exc:
            print(
                f"[HS80] Worker error: {exc}"
            )

            self.error.emit(str(exc))
            self.connection_changed.emit(False)

        finally:
            self._close_input_interface()
            self.receiver.disconnect()

    # =========================================================
    # STOP
    # =========================================================

    def stop(self):
        """Stop the worker cleanly."""

        self._running = False

        if self.isRunning():
            self.wait(1500)
