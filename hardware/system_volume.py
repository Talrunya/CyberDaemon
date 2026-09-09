import subprocess


def get_system_volume() -> int | None:
    """Return the current default PipeWire/PulseAudio volume as 0..100."""

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

        if result.returncode != 0:
            return None

        parts = result.stdout.strip().split()

        if not parts:
            return None

        value = float(parts[0])

        return max(0, min(100, round(value * 100)))

    except (
        FileNotFoundError,
        ValueError,
        subprocess.SubprocessError,
    ):
        return None