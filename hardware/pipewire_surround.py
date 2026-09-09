from __future__ import annotations

import json
import os
import signal
import shutil
import subprocess
import tempfile
import time
from pathlib import Path


class PipeWireSurround:
    """CyberDaemon HeSuVi 7.1 PipeWire surround engine."""

    INPUT_NAME = "cyberdaemon-surround"
    OUTPUT_NAME = "cyberdaemon-surround-output"
    DESCRIPTION = "CyberDaemon // HS80 MAX Surround 7.1"

    def __init__(self) -> None:
        self._process: subprocess.Popen[str] | None = None
        self._config_path: Path | None = None
        self._target_sink: str | None = None

    @staticmethod
    def _command_available(command: str) -> bool:
        return shutil.which(command) is not None

    @staticmethod
    def available() -> bool:
        return all(
            PipeWireSurround._command_available(command)
            for command in (
                "pipewire",
                "pw-dump",
                "pw-cli",
                "pw-link",
                "wpctl",
            )
        )

    @property
    def active(self) -> bool:
        return self._process is not None and self._process.poll() is None

    # ================================================================
    # HRIR
    # ================================================================

    @staticmethod
    def _hrir_candidates() -> list[Path]:
        xdg_data_home = os.environ.get("XDG_DATA_HOME")
        if xdg_data_home:
            base = Path(xdg_data_home)
        else:
            base = Path.home() / ".local" / "share"

        return [
            base / "pipewire" / "hrir_hesuvi" / "hrir.wav",
            Path("/usr/local/share/pipewire/hrir_hesuvi/hrir.wav"),
            Path("/usr/share/pipewire/hrir_hesuvi/hrir.wav"),
        ]

    @classmethod
    def _find_hrir(cls) -> Path | None:
        for path in cls._hrir_candidates():
            try:
                if path.is_file():
                    return path
            except OSError:
                pass
        return None

    # ================================================================
    # PIPEWIRE DISCOVERY
    # ================================================================

    @staticmethod
    def _pipewire_objects() -> list[dict]:
        try:
            result = subprocess.run(
                ["pw-dump"],
                capture_output=True,
                text=True,
                timeout=3.0,
                check=False,
            )
        except (OSError, subprocess.SubprocessError):
            return []

        if result.returncode != 0:
            return []

        try:
            data = json.loads(result.stdout)
        except (ValueError, TypeError):
            return []

        return data if isinstance(data, list) else []

    @classmethod
    def _find_hs80_sink(cls) -> str | None:
        """Find the physical Corsair HS80 MAX sink dynamically."""
        candidates: list[tuple[int, str]] = []

        for obj in cls._pipewire_objects():
            if obj.get("type") != "PipeWire:Interface:Node":
                continue

            info = obj.get("info")
            if not isinstance(info, dict):
                continue

            props = info.get("props")
            if not isinstance(props, dict):
                continue

            if props.get("media.class") != "Audio/Sink":
                continue
            if props.get("device.api") != "alsa":
                continue
            if props.get("device.bus") != "usb":
                continue

            node_name = props.get("node.name")
            if not isinstance(node_name, str) or not node_name:
                continue

            description = str(props.get("node.description", ""))
            text = description.lower()

            if "corsair" not in text:
                continue
            if "hs80" not in text:
                continue
            if "max" not in text:
                continue

            score = 30
            if "wireless" in text:
                score += 20
            if "gaming receiver" in text:
                score += 20
            if "analog" in text:
                score += 10

            candidates.append((score, node_name))

        if not candidates:
            return None

        candidates.sort(key=lambda item: item[0], reverse=True)
        return candidates[0][1]

    @classmethod
    def _node_id(cls, node_name: str) -> int | None:
        for obj in cls._pipewire_objects():
            if obj.get("type") != "PipeWire:Interface:Node":
                continue

            info = obj.get("info")
            if not isinstance(info, dict):
                continue

            props = info.get("props")
            if not isinstance(props, dict):
                continue

            if props.get("node.name") != node_name:
                continue

            obj_id = obj.get("id")
            if isinstance(obj_id, int):
                return obj_id

        return None

    # ================================================================
    # CONFIG
    # ================================================================

    @staticmethod
    def _escape(value: str) -> str:
        return value.replace("\\", "\\\\").replace('"', '\\"')

    def _build_config(self, hrir_path: Path) -> str:
        hrir = self._escape(str(hrir_path))
        description = self._escape(self.DESCRIPTION)

        return f'''context.properties = {{
    log.level = 0
}}

context.spa-libs = {{
    audio.convert.* = audioconvert/libspa-audioconvert
    support.* = support/libspa-support
}}

context.modules = [
    {{ name = libpipewire-module-protocol-native }}
    {{ name = libpipewire-module-client-node }}
    {{ name = libpipewire-module-adapter }}
    {{
        name = libpipewire-module-filter-chain
        args = {{
            node.description = "{description}"
            media.name = "{description}"

            filter.graph = {{
                nodes = [
                    {{ type = builtin label = copy name = copyFL }}
                    {{ type = builtin label = copy name = copyFR }}
                    {{ type = builtin label = copy name = copyFC }}
                    {{ type = builtin label = copy name = copyLFE }}
                    {{ type = builtin label = copy name = copyRL }}
                    {{ type = builtin label = copy name = copyRR }}
                    {{ type = builtin label = copy name = copySL }}
                    {{ type = builtin label = copy name = copySR }}

                    {{ type = builtin label = convolver name = convFL_L config = {{ filename = "{hrir}" channel = 0 }} }}
                    {{ type = builtin label = convolver name = convFL_R config = {{ filename = "{hrir}" channel = 1 }} }}
                    {{ type = builtin label = convolver name = convSL_L config = {{ filename = "{hrir}" channel = 2 }} }}
                    {{ type = builtin label = convolver name = convSL_R config = {{ filename = "{hrir}" channel = 3 }} }}
                    {{ type = builtin label = convolver name = convRL_L config = {{ filename = "{hrir}" channel = 4 }} }}
                    {{ type = builtin label = convolver name = convRL_R config = {{ filename = "{hrir}" channel = 5 }} }}
                    {{ type = builtin label = convolver name = convFC_L config = {{ filename = "{hrir}" channel = 6 }} }}
                    {{ type = builtin label = convolver name = convFR_R config = {{ filename = "{hrir}" channel = 7 }} }}
                    {{ type = builtin label = convolver name = convFR_L config = {{ filename = "{hrir}" channel = 8 }} }}
                    {{ type = builtin label = convolver name = convSR_R config = {{ filename = "{hrir}" channel = 9 }} }}
                    {{ type = builtin label = convolver name = convSR_L config = {{ filename = "{hrir}" channel = 10 }} }}
                    {{ type = builtin label = convolver name = convRR_R config = {{ filename = "{hrir}" channel = 11 }} }}
                    {{ type = builtin label = convolver name = convRR_L config = {{ filename = "{hrir}" channel = 12 }} }}
                    {{ type = builtin label = convolver name = convFC_R config = {{ filename = "{hrir}" channel = 13 }} }}
                    {{ type = builtin label = convolver name = convLFE_L config = {{ filename = "{hrir}" channel = 6 }} }}
                    {{ type = builtin label = convolver name = convLFE_R config = {{ filename = "{hrir}" channel = 13 }} }}

                    {{ type = builtin label = mixer name = mixL }}
                    {{ type = builtin label = mixer name = mixR }}
                ]

                links = [
                    {{ output = "copyFL:Out" input = "convFL_L:In" }}
                    {{ output = "copyFL:Out" input = "convFL_R:In" }}
                    {{ output = "copySL:Out" input = "convSL_L:In" }}
                    {{ output = "copySL:Out" input = "convSL_R:In" }}
                    {{ output = "copyRL:Out" input = "convRL_L:In" }}
                    {{ output = "copyRL:Out" input = "convRL_R:In" }}
                    {{ output = "copyFC:Out" input = "convFC_L:In" }}
                    {{ output = "copyFR:Out" input = "convFR_R:In" }}
                    {{ output = "copyFR:Out" input = "convFR_L:In" }}
                    {{ output = "copySR:Out" input = "convSR_R:In" }}
                    {{ output = "copySR:Out" input = "convSR_L:In" }}
                    {{ output = "copyRR:Out" input = "convRR_R:In" }}
                    {{ output = "copyRR:Out" input = "convRR_L:In" }}
                    {{ output = "copyFC:Out" input = "convFC_R:In" }}
                    {{ output = "copyLFE:Out" input = "convLFE_L:In" }}
                    {{ output = "copyLFE:Out" input = "convLFE_R:In" }}

                    {{ output = "convFL_L:Out" input = "mixL:In 1" }}
                    {{ output = "convFL_R:Out" input = "mixR:In 1" }}
                    {{ output = "convSL_L:Out" input = "mixL:In 2" }}
                    {{ output = "convSL_R:Out" input = "mixR:In 2" }}
                    {{ output = "convRL_L:Out" input = "mixL:In 3" }}
                    {{ output = "convRL_R:Out" input = "mixR:In 3" }}
                    {{ output = "convFC_L:Out" input = "mixL:In 4" }}
                    {{ output = "convFC_R:Out" input = "mixR:In 4" }}
                    {{ output = "convFR_R:Out" input = "mixR:In 5" }}
                    {{ output = "convFR_L:Out" input = "mixL:In 5" }}
                    {{ output = "convSR_R:Out" input = "mixR:In 6" }}
                    {{ output = "convSR_L:Out" input = "mixL:In 6" }}
                    {{ output = "convRR_R:Out" input = "mixR:In 7" }}
                    {{ output = "convRR_L:Out" input = "mixL:In 7" }}
                    {{ output = "convLFE_R:Out" input = "mixR:In 8" }}
                    {{ output = "convLFE_L:Out" input = "mixL:In 8" }}
                ]

                inputs = [
                    "copyFL:In" "copyFR:In" "copyFC:In" "copyLFE:In"
                    "copyRL:In" "copyRR:In" "copySL:In" "copySR:In"
                ]

                outputs = [
                    "mixL:Out"
                    "mixR:Out"
                ]
            }}

            capture.props = {{
                node.name = "{self.INPUT_NAME}"
                node.description = "{description}"
                media.class = Audio/Sink
                audio.channels = 8
                audio.position = [ FL FR FC LFE RL RR SL SR ]
            }}

            playback.props = {{
                node.name = "{self.OUTPUT_NAME}"
                node.description = "{description} Output"
                node.passive = true
                audio.channels = 2
                audio.position = [ FL FR ]
            }}
        }}
    }}
]
'''

    # ================================================================
    # ROUTING
    # ================================================================

    def _connect_output(self, target: str) -> bool:
        """Connect stereo output to a dynamically supplied target node."""
        try:
            result = subprocess.run(
                [
                    "pw-cli",
                    "create-link",
                    self.OUTPUT_NAME,
                    "*",
                    target,
                    "*",
                ],
                capture_output=True,
                text=True,
                timeout=5.0,
                check=False,
            )
        except (OSError, subprocess.SubprocessError) as exc:
            print("[CyberDaemon Surround] create-link failed:", exc)
            return False

        if result.returncode != 0:
            error = result.stderr.strip() or result.stdout.strip()
            if "exist" not in error.lower() and "already" not in error.lower():
                print("[CyberDaemon Surround] Link failed:", error)
                return False

        return True

    def _set_default(self) -> bool:
        node_id = self._node_id(self.INPUT_NAME)
        if node_id is None:
            print("[CyberDaemon Surround] Surround input node ID not found.")
            return False

        try:
            result = subprocess.run(
                ["wpctl", "set-default", str(node_id)],
                capture_output=True,
                text=True,
                timeout=3.0,
                check=False,
            )
        except (OSError, subprocess.SubprocessError) as exc:
            print("[CyberDaemon Surround] set-default failed:", exc)
            return False

        if result.returncode != 0:
            print("[CyberDaemon Surround] set-default failed:", result.stderr.strip())
            return False

        return True

    def ensure_target(self, target: str) -> bool:
        """Reconnect the running surround output to a newly recreated target."""
        if not self.active:
            return False

        if not self._connect_output(target):
            return False

        self._target_sink = target
        return self._set_default()

    # ================================================================
    # START / STOP
    # ================================================================

    def start(self, target_sink: str | None = None) -> bool:
        """
        Start surround and route its stereo result to target_sink.

        If target_sink is omitted, the physical HS80 MAX sink is detected.
        When a target is supplied (CyberDaemon EQ), the target is resolved
        by PipeWire node name at runtime.
        """
        if self.active:
            if target_sink is not None and target_sink != self._target_sink:
                return self.ensure_target(target_sink)
            if target_sink is not None:
                return self.ensure_target(target_sink)
            return True

        if not self.available():
            print("[CyberDaemon Surround] Required PipeWire tools are missing.")
            return False

        hrir_path = self._find_hrir()
        if hrir_path is None:
            print("[CyberDaemon Surround] No HeSuVi HRIR file found.")
            return False

        if target_sink is None:
            target_sink = self._find_hs80_sink()
            if target_sink is None:
                print("[CyberDaemon Surround] HS80 MAX sink not found.")
                return False

        print("[CyberDaemon Surround] Target:", target_sink)
        print("[CyberDaemon Surround] Using HRIR:", hrir_path)

        runtime_dir = os.environ.get("XDG_RUNTIME_DIR")
        try:
            fd, filename = tempfile.mkstemp(
                prefix="cyberdaemon-surround-",
                suffix=".conf",
                dir=runtime_dir or None,
                text=True,
            )
        except OSError as exc:
            print("[CyberDaemon Surround] Could not create config:", exc)
            return False

        os.close(fd)
        self._config_path = Path(filename)

        try:
            self._config_path.write_text(
                self._build_config(hrir_path),
                encoding="utf-8",
            )
        except OSError as exc:
            print("[CyberDaemon Surround] Could not write config:", exc)
            self.stop()
            return False

        try:
            self._process = subprocess.Popen(
                ["pipewire", "-c", str(self._config_path)],
                stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.PIPE,
                text=True,
                env=os.environ.copy(),
                start_new_session=True,
            )
        except OSError as exc:
            print("[CyberDaemon Surround] Could not start filter-chain:", exc)
            self.stop()
            return False

        deadline = time.monotonic() + 5.0
        while time.monotonic() < deadline:
            if self._process.poll() is not None:
                error = ""
                if self._process.stderr is not None:
                    try:
                        error = self._process.stderr.read().strip()
                    except OSError:
                        pass
                if error:
                    print("[CyberDaemon Surround] PipeWire:", error)
                self.stop()
                return False

            nodes = self._node_names()
            if self.INPUT_NAME in nodes and self.OUTPUT_NAME in nodes:
                break
            time.sleep(0.1)
        else:
            print("[CyberDaemon Surround] Filter nodes did not appear.")
            self.stop()
            return False

        if not self._connect_output(target_sink):
            self.stop()
            return False

        self._target_sink = target_sink

        if not self._set_default():
            self.stop()
            return False

        print("[CyberDaemon Surround] 7.1 active ->", target_sink)
        return True

    @classmethod
    def _node_names(cls) -> set[str]:
        names: set[str] = set()
        for obj in cls._pipewire_objects():
            if obj.get("type") != "PipeWire:Interface:Node":
                continue
            info = obj.get("info")
            if not isinstance(info, dict):
                continue
            props = info.get("props")
            if not isinstance(props, dict):
                continue
            node_name = props.get("node.name")
            if isinstance(node_name, str):
                names.add(node_name)
        return names

    def stop(self) -> None:
        process = self._process
        self._process = None

        if process is not None and process.poll() is None:
            try:
                os.killpg(process.pid, signal.SIGTERM)
            except ProcessLookupError:
                pass

            try:
                process.wait(timeout=1.5)
            except subprocess.TimeoutExpired:
                try:
                    os.killpg(process.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
                try:
                    process.wait(timeout=1.0)
                except subprocess.TimeoutExpired:
                    pass

        time.sleep(0.15)

        if self._config_path is not None:
            try:
                self._config_path.unlink(missing_ok=True)
            except OSError:
                pass

        self._config_path = None
        self._target_sink = None


__all__ = ["PipeWireSurround"]
