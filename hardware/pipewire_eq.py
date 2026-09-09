from __future__ import annotations

import json
import os
import re
import shutil
import signal
import subprocess
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


EQ_FREQUENCIES = (
    32,
    64,
    125,
    250,
    500,
    1000,
    2000,
    4000,
    8000,
    16000,
)


@dataclass(frozen=True)
class EQState:
    bands: tuple[float, ...]


class PipeWireEQ:
    """
    CyberDaemon 10-band PipeWire EQ.

    The EQ runs as a normal PipeWire filter-chain client.

    Audio path:

        Applications
             ↓
        cyberdaemon-eq
             ↓
        cyberdaemon-eq-output
             ↓
        detected HS80 MAX sink

    PipeWire numeric node IDs are NEVER stored. They are only discovered
    temporarily when the current graph has to be inspected.

    The HS80 sink is discovered dynamically by its PipeWire node name.
    """

    NODE_NAME = "cyberdaemon-eq"
    OUTPUT_NAME = "cyberdaemon-eq-output"
    DESCRIPTION = "CyberDaemon // HS80 MAX EQ"

    def __init__(self) -> None:
        self._process: subprocess.Popen[str] | None = None
        self._config_path: Path | None = None
        self._target_sink: str | None = None

        self._state = EQState(
            (0.0,) * len(EQ_FREQUENCIES)
        )

    # ================================================================
    # BASIC STATE
    # ================================================================

    @staticmethod
    def available() -> bool:
        """
        Check whether the PipeWire tools required by CyberDaemon exist.

        wpctl and pw-link are optional. The standalone filter-chain and
        graph discovery work with pipewire + pw-cli, avoiding a mandatory
        WirePlumber configuration/runtime dependency.
        """
        return all(
            shutil.which(command) is not None
            for command in (
                "pipewire",
                "pw-cli",
            )
        )

    @property
    def state(self) -> EQState:
        return self._state

    @property
    def target_sink(self) -> str | None:
        """
        Current dynamically detected HS80 PipeWire sink.
        """
        return self._target_sink

    # ================================================================
    # EQ VALUES
    # ================================================================

    @staticmethod
    def _normalise_bands(
        bands: Iterable[float],
    ) -> tuple[float, ...]:
        values = list(bands)

        if len(values) != len(EQ_FREQUENCIES):
            raise ValueError(
                f"Expected {len(EQ_FREQUENCIES)} EQ bands, "
                f"got {len(values)}."
            )

        return tuple(
            max(
                -12.0,
                min(
                    12.0,
                    float(value),
                ),
            )
            for value in values
        )

    # ================================================================
    # HS80 DISCOVERY
    # ================================================================

    def _find_hs80_sink(self) -> str | None:
        """
        Find the current HS80 MAX analog playback node.

        No PipeWire numeric node ID is stored.
        """

        # ------------------------------------------------------------
        # First try wpctl status -n
        # ------------------------------------------------------------

        try:
            result = subprocess.run(
                [
                    "wpctl",
                    "status",
                    "-n",
                ],
                capture_output=True,
                text=True,
                timeout=3.0,
                check=False,
            )
        except (
            OSError,
            subprocess.SubprocessError,
        ) as exc:
            print(
                "[CyberDaemon EQ] HS80 discovery failed:",
                exc,
            )
            return None

        pattern = re.compile(
            r"(alsa_output\.usb-Corsair_"
            r"CORSAIR_HS80_MAX_WIRELESS_Gaming_Receiver_"
            r"[^\s]+-00\.analog-stereo)"
        )

        for line in result.stdout.splitlines():
            if (
                "CORSAIR HS80 MAX WIRELESS Gaming Receiver"
                not in line
            ):
                continue

            if (
                "Analoges Stereo" not in line
                and "analog-stereo" not in line
            ):
                continue

            match = pattern.search(line)

            if match:
                return match.group(1)

        # ------------------------------------------------------------
        # Fallback: inspect raw PipeWire Node objects
        # ------------------------------------------------------------

        try:
            result = subprocess.run(
                [
                    "pw-cli",
                    "ls",
                    "Node",
                ],
                capture_output=True,
                text=True,
                timeout=3.0,
                check=False,
            )
        except (
            OSError,
            subprocess.SubprocessError,
        ):
            return None

        for match in re.finditer(
            r'node\.name = "([^"]+)"',
            result.stdout,
        ):
            node_name = match.group(1)

            if (
                node_name.startswith(
                    "alsa_output.usb-Corsair_"
                    "CORSAIR_HS80_MAX_WIRELESS_Gaming_Receiver_"
                )
                and node_name.endswith(
                    "-00.analog-stereo"
                )
            ):
                return node_name

        return None

    # ================================================================
    # PIPEWIRE CONFIG
    # ================================================================

    def _build_config(
        self,
        bands: tuple[float, ...],
    ) -> str:
        nodes: list[str] = []
        links: list[str] = []

        for index, (
            frequency,
            gain,
        ) in enumerate(
            zip(
                EQ_FREQUENCIES,
                bands,
            ),
            start=1,
        ):
            nodes.append(
                "                    {\n"
                "                        type = builtin\n"
                f"                        name = eq_{index}\n"
                "                        label = bq_peaking\n"
                f'                        control = {{ '
                f'"Freq" = {float(frequency):.1f} '
                f'"Q" = 1.0 '
                f'"Gain" = {float(gain):.2f} '
                "}\n"
                "                    }"
            )

            if index > 1:
                links.append(
                    "                    { "
                    f'output = "eq_{index - 1}:Out" '
                    f'input = "eq_{index}:In" '
                    "}"
                )

        node_text = ",\n".join(nodes)
        link_text = ",\n".join(links)

        return f"""# ============================================================
# CyberDaemon generated PipeWire EQ
# ============================================================
#
# Standalone PipeWire filter-chain configuration.
# No manual WirePlumber filter-chain configuration is required.
# Generated automatically by CyberDaemon.
#

context.properties = {{
    log.level = 0
}}

# PipeWire SPA libraries required by the standalone filter-chain.
context.spa-libs = {{
    audio.convert.* = audioconvert/libspa-audioconvert
    support.* = support/libspa-support
}}

context.modules = [

    # Native PipeWire communication.
    {{
        name = libpipewire-module-protocol-native
    }}

    # Allows filter-chain to create client-side nodes.
    {{
        name = libpipewire-module-client-node
    }}

    # Provides the adapter factory required by filter-chain.
    {{
        name = libpipewire-module-adapter
    }}

    # CyberDaemon EQ filter-chain.
    {{
        name = libpipewire-module-filter-chain

        args = {{
            node.description = "{self.DESCRIPTION}"
            media.name = "{self.DESCRIPTION}"

            filter.graph = {{
                nodes = [
{node_text}
                ]

                links = [
{link_text}
                ]
            }}

            audio.channels = 2
            audio.position = [ FL FR ]

            capture.props = {{
                node.name = "{self.NODE_NAME}"
                node.description = "{self.DESCRIPTION}"
                media.class = Audio/Sink
                node.passive = true
            }}

            playback.props = {{
                node.name = "{self.OUTPUT_NAME}"
                node.description = "{self.DESCRIPTION} Output"
                node.passive = true
            }}
        }}
    }}
]
"""

    # ================================================================
    # NODE DISCOVERY
    # ================================================================

    def _node_ids(self) -> dict[str, int]:
        """
        Find the current IDs of our two filter nodes.

        These IDs are temporary and are never persisted.
        """

        try:
            result = subprocess.run(
                [
                    "pw-cli",
                    "ls",
                    "Node",
                ],
                capture_output=True,
                text=True,
                timeout=3.0,
                check=False,
            )
        except (
            OSError,
            subprocess.SubprocessError,
        ):
            return {}

        ids: dict[str, int] = {}
        current_id: int | None = None

        for line in result.stdout.splitlines():
            id_match = re.match(
                r"\s*id\s+(\d+),",
                line,
            )

            if id_match:
                current_id = int(
                    id_match.group(1)
                )
                continue

            name_match = re.search(
                r'node\.name = "([^"]+)"',
                line,
            )

            if (
                current_id is None
                or name_match is None
            ):
                continue

            node_name = name_match.group(1)

            if node_name in (
                self.NODE_NAME,
                self.OUTPUT_NAME,
            ):
                ids[node_name] = current_id

            current_id = None

        return ids

    def _wait_for_nodes(
        self,
        timeout: float = 4.0,
    ) -> bool:
        """
        Wait until both filter-chain nodes are visible.
        """

        deadline = (
            time.monotonic()
            + timeout
        )

        while time.monotonic() < deadline:
            process = self._process

            if (
                process is not None
                and process.poll() is not None
            ):
                self._print_process_error()
                return False

            ids = self._node_ids()

            if (
                self.NODE_NAME in ids
                and self.OUTPUT_NAME in ids
            ):
                return True

            time.sleep(0.10)

        return False

    # ================================================================
    # PROCESS CONTROL
    # ================================================================

    def _start_process(
        self,
        config_path: Path,
    ) -> bool:
        try:
            self._process = subprocess.Popen(
                [
                    "pipewire",
                    "-c",
                    str(config_path),
                ],
                stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.PIPE,
                text=True,
                env=os.environ.copy(),
                start_new_session=True,
            )

        except OSError as exc:
            print(
                "[CyberDaemon EQ] "
                "Could not start filter-chain:",
                exc,
            )

            self._process = None

            return False

        return True

    def _print_process_error(self) -> None:
        process = self._process

        if (
            process is None
            or process.stderr is None
        ):
            return

        try:
            error = process.stderr.read().strip()

        except OSError:
            return

        if error:
            print(
                "[CyberDaemon EQ] PipeWire:",
                error,
            )

    def _stop_process(self) -> None:
        process = self._process
        self._process = None

        if (
            process is not None
            and process.poll() is None
        ):
            try:
                os.killpg(
                    process.pid,
                    signal.SIGTERM,
                )
            except ProcessLookupError:
                pass

            try:
                process.wait(
                    timeout=1.5
                )

            except subprocess.TimeoutExpired:
                try:
                    os.killpg(
                        process.pid,
                        signal.SIGKILL,
                    )
                except ProcessLookupError:
                    pass

                try:
                    process.wait(
                        timeout=1.0
                    )
                except subprocess.TimeoutExpired:
                    pass

        # Give PipeWire a moment to remove the nodes.
        time.sleep(0.15)

        if self._config_path is not None:
            try:
                self._config_path.unlink(
                    missing_ok=True
                )
            except OSError:
                pass

            self._config_path = None

        self._target_sink = None

    # ================================================================
    # ROUTING
    # ================================================================

    def _connect_output(
    self,
    target_sink: str,
) -> bool:
        """
        Connect CyberDaemon EQ output to the dynamically detected HS80 sink.

        No fixed PipeWire node IDs or port object IDs are used.
        PipeWire resolves the node names and automatically matches
        the corresponding FL/FR ports.
        """

        try:
            result = subprocess.run(
                [
                    "pw-cli",
                    "create-link",
                    self.OUTPUT_NAME,
                    "*",
                    target_sink,
                    "*",
                ],
                capture_output=True,
                text=True,
                timeout=5.0,
                check=False,
            )

        except (
            OSError,
            subprocess.SubprocessError,
        ) as exc:
            print(
                "[CyberDaemon EQ] "
                "create-link failed:",
                exc,
            )
            return False

        if result.returncode != 0:
            error = (
                result.stderr.strip()
                or result.stdout.strip()
            )

            if (
                "exist" in error.lower()
                or "already" in error.lower()
            ):
                return True

            print(
                "[CyberDaemon EQ] "
                "Link failed:",
                self.OUTPUT_NAME,
                "->",
                target_sink,
                error,
            )
            return False

        print(
            "[CyberDaemon EQ] "
            f"Linked {self.OUTPUT_NAME} -> {target_sink}"
        )

        return True




    def _set_default(self) -> bool:
        """
        Prefer wpctl when available.

        Without wpctl, keep the EQ fully usable without requiring an extra
        WirePlumber configuration. The direct PipeWire fallback marks the
        CyberDaemon EQ node as preferred, while the actual audio link remains
        managed by this class.
        """

        node_id = self._node_ids().get(
            self.NODE_NAME
        )

        if node_id is None:
            print(
                "[CyberDaemon EQ] "
                "EQ node ID not found."
            )
            return False

        wpctl = shutil.which("wpctl")

        if wpctl is not None:
            try:
                result = subprocess.run(
                    [
                        wpctl,
                        "set-default",
                        str(node_id),
                    ],
                    capture_output=True,
                    text=True,
                    timeout=3.0,
                    check=False,
                )
            except (
                OSError,
                subprocess.SubprocessError,
            ) as exc:
                print(
                    "[CyberDaemon EQ] "
                    "wpctl unavailable:",
                    exc,
                )
            else:
                if result.returncode == 0:
                    return True

                print(
                    "[CyberDaemon EQ] "
                    "wpctl set-default failed:",
                    result.stderr.strip(),
                )

        # No hard WirePlumber dependency: keep our own PipeWire node
        # available and preferred without requiring user configuration.
        try:
            result = subprocess.run(
                [
                    "pw-cli",
                    "set-param",
                    str(node_id),
                    "Props",
                    json.dumps(
                        {
                            "priority.session": 2000,
                            "priority.driver": 2000,
                        }
                    ),
                ],
                capture_output=True,
                text=True,
                timeout=3.0,
                check=False,
            )
        except (
            OSError,
            subprocess.SubprocessError,
        ) as exc:
            print(
                "[CyberDaemon EQ] "
                "PipeWire preference fallback failed:",
                exc,
            )
            return False

        if result.returncode != 0:
            print(
                "[CyberDaemon EQ] "
                "PipeWire preference fallback rejected:",
                result.stderr.strip(),
            )
            return False

        print(
            "[CyberDaemon EQ] "
            "Using direct PipeWire node preference "
            "(wpctl not available)."
        )

        return True

    def set_default(self) -> bool:
        """Make the CyberDaemon EQ sink the default output."""
        return self._set_default()

    def _update_live_gains(
        self,
        bands: tuple[float, ...],
    ) -> bool:
        """
        Update all EQ gains on the already-running filter chain.

        No PipeWire restart, no routing changes and no new filter graph.
        """
        node_id = self._node_ids().get(
            self.NODE_NAME
        )

        if node_id is None:
            print(
                "[CyberDaemon EQ] "
                "Live update: EQ node ID not found."
            )
            return False

        params: list[object] = []

        for index, gain in enumerate(
            bands,
            start=1,
        ):
            params.extend(
                [
                    f"eq_{index}:Gain",
                    float(gain),
                ]
            )

        payload = json.dumps(
            {
                "params": params,
            }
        )

        try:
            result = subprocess.run(
                [
                    "pw-cli",
                    "set-param",
                    str(node_id),
                    "Props",
                    payload,
                ],
                capture_output=True,
                text=True,
                timeout=3.0,
                check=False,
            )
        except (
            OSError,
            subprocess.SubprocessError,
        ) as exc:
            print(
                "[CyberDaemon EQ] "
                "Live update failed:",
                exc,
            )
            return False

        if result.returncode != 0:
            print(
                "[CyberDaemon EQ] "
                "Live update rejected:",
                result.stderr.strip(),
            )
            return False

        self._state = EQState(
            bands
        )

        print(
            "[CyberDaemon EQ] "
            "Live gains updated:",
            list(bands),
        )

        return True
    # ================================================================
    # PUBLIC API
    # ================================================================

    def apply(
    self,
    bands: Iterable[float],
) -> bool:
        """
        Apply a complete 10-band EQ curve.

        If the EQ graph is already running on the same HS80 sink,
        update only the filter gains without rebuilding the graph.
        """

        normalised = self._normalise_bands(
            bands
        )

        if not self.available():
            print(
                "[CyberDaemon EQ] "
                "Required PipeWire tools are missing."
            )
            return False

        target_sink = self._find_hs80_sink()

        if target_sink is None:
            print(
                "[CyberDaemon EQ] "
                "HS80 MAX sink not found."
            )
            return False

        # ------------------------------------------------------------
        # LIVE UPDATE
        # ------------------------------------------------------------
        # Keep the existing PipeWire graph alive when possible.
        # Only the EQ gains are changed.
        if (
            self._process is not None
            and self._process.poll() is None
            and self._target_sink == target_sink
        ):
            if self._update_live_gains(
                normalised
            ):
                return True

            print(
                "[CyberDaemon EQ] "
                "Live update failed; rebuilding EQ graph."
            )

        # ------------------------------------------------------------
        # FULL REBUILD
        # ------------------------------------------------------------
        # Used for first start, changed sink, or failed live update.
        self._stop_process()

        runtime_dir = os.environ.get(
            "XDG_RUNTIME_DIR"
        )

        fd, filename = tempfile.mkstemp(
            prefix="cyberdaemon-eq-",
            suffix=".conf",
            dir=runtime_dir or None,
            text=True,
        )

        os.close(fd)

        config_path = Path(filename)

        try:
            config_path.write_text(
                self._build_config(
                    normalised
                ),
                encoding="utf-8",
            )

        except OSError as exc:
            print(
                "[CyberDaemon EQ] "
                "Could not write config:",
                exc,
            )

            try:
                config_path.unlink(
                    missing_ok=True
                )
            except OSError:
                pass

            return False

        self._config_path = config_path

        if not self._start_process(
            config_path
        ):
            self._stop_process()
            return False

        if not self._wait_for_nodes():
            print(
                "[CyberDaemon EQ] "
                "Filter nodes did not appear."
            )

            self._stop_process()
            return False

        if not self._connect_output(
            target_sink
        ):
            self._stop_process()
            return False

        if not self._set_default():
            self._stop_process()
            return False

        self._state = EQState(
            normalised
        )

        self._target_sink = target_sink

        print(
            "[CyberDaemon EQ] "
            "EQ active:",
            list(normalised),
        )

        print(
            "[CyberDaemon EQ] "
            "Target:",
            target_sink,
        )

        return True
        def apply_profile(
            self,
            profile,
        ) -> bool:
            """
            Apply the EQ curve stored in a CyberDaemon profile.
            """

            eq = getattr(
                profile,
                "eq",
                None,
            )

            bands = (
                getattr(
                    eq,
                    "bands",
                    None,
                )
                if eq is not None
                else None
            )

            if bands is None:
                print(
                    "[CyberDaemon EQ] "
                    "Profile has no EQ bands:",
                    getattr(
                        profile,
                        "name",
                        "<unknown>",
                    ),
                )
                return False

            print(
                "[CyberDaemon EQ] "
                "Applying profile:",
                getattr(
                    profile,
                    "name",
                    "<unknown>",
                ),
            )

            return self.apply(bands)

    def flat(self) -> bool:
        """
        Apply a completely flat EQ.
        """

        return self.apply(
            (0.0,) * len(EQ_FREQUENCIES)
        )

    def stop(self) -> None:
        """
        Stop and remove the CyberDaemon EQ.
        """

        self._stop_process()


__all__ = [
    "EQ_FREQUENCIES",
    "EQState",
    "PipeWireEQ",
]