from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import List
import json
import os
import tempfile


APP_NAME = "CyberDaemon"


def _profile_file_path() -> Path:
    """
    Return the writable per-user profile store.

    XDG_CONFIG_HOME is honored when set; otherwise ~/.config is used.
    This keeps profiles outside the read-only AppImage bundle and works
    consistently across Linux distributions.
    """

    config_home = os.environ.get(
        "XDG_CONFIG_HOME"
    )

    if config_home:
        base = Path(config_home).expanduser()
    else:
        base = (
            Path.home()
            / ".config"
        )

    return (
        base
        / APP_NAME
        / "profiles.json"
    )


PROFILE_FILE = _profile_file_path()


@dataclass
class EQSettings:
    """Equalizer settings belonging to a headset profile."""

    preset: str = "Pure Direct"
    bands: List[float] = field(
        default_factory=lambda: [0.0] * 10
    )


@dataclass
class RGBSettings:
    """RGB lighting settings belonging to a headset profile."""

    effect: str = "Static"
    color: str = "#00E5FF"
    brightness: int = 100


@dataclass
class SurroundSettings:
    """Software profile state for virtual surround."""

    enabled: bool = False


@dataclass
class Profile:
    """Complete CyberDaemon headset software profile."""

    name: str

    eq: EQSettings = field(
        default_factory=EQSettings
    )

    sidetone: int = 0

    rgb: RGBSettings = field(
        default_factory=RGBSettings
    )

    surround: SurroundSettings = field(
        default_factory=SurroundSettings
    )


class ProfileManager:
    """Manage HS80 MAX profiles and persist them to profiles.json."""

    FILE_VERSION = 2

    def __init__(self, profile_file=None):
        self.profile_file = (
            Path(profile_file).expanduser().resolve()
            if profile_file is not None
            else PROFILE_FILE
        )

        self.profiles = self._default_profiles()
        self.current_index = 0

        self.load()

    # ============================================================
    # DEFAULT PROFILES
    # ============================================================

    @staticmethod
    def _default_profiles():
        return [
            Profile(
                name="Clear Chat",
                eq=EQSettings(
                    preset="Clear Chat"
                ),
                sidetone=30,
                rgb=RGBSettings(
                    effect="Static",
                    color="#00E5FF",
                    brightness=100,
                ),
                surround=SurroundSettings(
                    enabled=True
                ),
            ),
            Profile(
                name="FPS",
                eq=EQSettings(
                    preset="FPS Competition"
                ),
                sidetone=20,
                rgb=RGBSettings(
                    effect="Static",
                    color="#FF00FF",
                    brightness=80,
                ),
                surround=SurroundSettings(
                    enabled=True
                ),
            ),
            Profile(
                name="Music",
                eq=EQSettings(
                    preset="Pure Direct"
                ),
                sidetone=0,
                rgb=RGBSettings(
                    effect="Static",
                    color="#00FF88",
                    brightness=100,
                ),
                surround=SurroundSettings(
                    enabled=False
                ),
            ),
            Profile(
                name="Bass Boost",
                eq=EQSettings(
                    preset="Bass Boost"
                ),
                sidetone=20,
                rgb=RGBSettings(
                    effect="Static",
                    color="#FF4400",
                    brightness=100,
                ),
                surround=SurroundSettings(
                    enabled=True
                ),
            ),
            Profile(
                name="MMO",
                eq=EQSettings(
                    preset="Movie Theater"
                ),
                sidetone=20,
                rgb=RGBSettings(
                    effect="Static",
                    color="#AA66FF",
                    brightness=100,
                ),
                surround=SurroundSettings(
                    enabled=True
                ),
            ),
        ]

    # ============================================================
    # ACTIVE PROFILE
    # ============================================================

    @property
    def current_profile(self) -> Profile:
        if not self.profiles:
            raise RuntimeError("No profiles available.")

        self.current_index = max(
            0,
            min(
                self.current_index,
                len(self.profiles) - 1,
            ),
        )

        return self.profiles[self.current_index]

    # ============================================================
    # LOAD / SAVE
    # ============================================================

    def _migrate_legacy_profile_store(self) -> bool:
        """
        Migrate an existing repository-local profiles.json once.

        This preserves the user's existing profiles when moving from the
        old development layout to the writable XDG config location.
        """

        if self.profile_file.exists():
            return False

        legacy_file = (
            Path(__file__).resolve().parent.parent
            / "profiles"
            / "profiles.json"
        )

        if (
            not legacy_file.exists()
            or legacy_file == self.profile_file
        ):
            return False

        try:
            self.profile_file.parent.mkdir(
                parents=True,
                exist_ok=True,
            )
            shutil.copy2(
                legacy_file,
                self.profile_file,
            )

            print(
                "[CyberDaemon] Migrated profiles to: "
                f"{self.profile_file}"
            )

            return True

        except OSError as exc:
            print(
                "[CyberDaemon] Profile migration failed: "
                f"{exc}"
            )
            return False

    def load(self):
        """Load profiles from JSON.

        Existing files without the newer surround field remain valid.
        Missing surround data defaults to OFF.
        """

        self._migrate_legacy_profile_store()

        if not self.profile_file.exists():
            self.profiles = self._default_profiles()
            self.current_index = 0
            self.save()

            print(
                f"[CyberDaemon] Created profile store: "
                f"{self.profile_file}"
            )
            return

        try:
            with self.profile_file.open(
                "r",
                encoding="utf-8",
            ) as handle:
                data = json.load(handle)

            loaded_profiles = data.get(
                "profiles",
                [],
            )

            loaded_index = int(
                data.get(
                    "current_index",
                    0,
                )
            )

            profiles = []

            for raw_profile in loaded_profiles:
                if not isinstance(
                    raw_profile,
                    dict,
                ):
                    continue

                eq_data = raw_profile.get(
                    "eq",
                    {},
                )

                if not isinstance(
                    eq_data,
                    dict,
                ):
                    eq_data = {}

                rgb_data = raw_profile.get(
                    "rgb",
                    {},
                )

                if not isinstance(
                    rgb_data,
                    dict,
                ):
                    rgb_data = {}

                surround_data = raw_profile.get(
                    "surround",
                    {},
                )

                if isinstance(
                    surround_data,
                    bool,
                ):
                    surround_data = {
                        "enabled": surround_data
                    }

                if not isinstance(
                    surround_data,
                    dict,
                ):
                    surround_data = {}

                bands = eq_data.get(
                    "bands",
                    [0.0] * 10,
                )

                if not isinstance(
                    bands,
                    list,
                ):
                    bands = [0.0] * 10

                normalized_bands = []

                for value in bands[:10]:
                    try:
                        normalized_bands.append(
                            float(value)
                        )
                    except (
                        TypeError,
                        ValueError,
                    ):
                        normalized_bands.append(
                            0.0
                        )

                normalized_bands += [
                    0.0
                ] * (
                    10 - len(normalized_bands)
                )

                profile = Profile(
                    name=str(
                        raw_profile.get(
                            "name",
                            "Unnamed",
                        )
                    ),
                    eq=EQSettings(
                        preset=str(
                            eq_data.get(
                                "preset",
                                "Pure Direct",
                            )
                        ),
                        bands=normalized_bands,
                    ),
                    sidetone=max(
                        0,
                        min(
                            100,
                            int(
                                raw_profile.get(
                                    "sidetone",
                                    0,
                                )
                            ),
                        ),
                    ),
                    rgb=RGBSettings(
                        effect=str(
                            rgb_data.get(
                                "effect",
                                "Static",
                            )
                        ),
                        color=str(
                            rgb_data.get(
                                "color",
                                "#00E5FF",
                            )
                        ),
                        brightness=max(
                            0,
                            min(
                                100,
                                int(
                                    rgb_data.get(
                                        "brightness",
                                        100,
                                    )
                                ),
                            ),
                        ),
                    ),
                    surround=SurroundSettings(
                        enabled=bool(
                            surround_data.get(
                                "enabled",
                                False,
                            )
                        )
                    ),
                )

                profiles.append(profile)

            if not profiles:
                raise ValueError(
                    "Profile file contains no profiles."
                )

            self.profiles = profiles

            self.current_index = max(
                0,
                min(
                    loaded_index,
                    len(self.profiles) - 1,
                ),
            )

            print(
                f"[CyberDaemon] Loaded {len(self.profiles)} "
                f"profiles from {self.profile_file}"
            )

            print(
                f"[CyberDaemon] Active profile: "
                f"{self.current_profile.name}"
            )

        except (
            OSError,
            ValueError,
            TypeError,
            json.JSONDecodeError,
        ) as exc:
            print(
                f"[CyberDaemon] Profile load failed: {exc}"
            )

            print(
                "[CyberDaemon] Recreating default profiles."
            )

            self.profiles = self._default_profiles()
            self.current_index = 0
            self.save()

    def save(self):
        """Atomically persist all profiles."""

        self.profile_file.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        data = {
            "version": self.FILE_VERSION,
            "current_index": self.current_index,
            "profiles": [
                asdict(profile)
                for profile in self.profiles
            ],
        }

        fd, temp_name = tempfile.mkstemp(
            prefix=".profiles-",
            suffix=".tmp",
            dir=str(
                self.profile_file.parent
            ),
        )

        try:
            with os.fdopen(
                fd,
                "w",
                encoding="utf-8",
            ) as handle:
                json.dump(
                    data,
                    handle,
                    indent=4,
                    ensure_ascii=False,
                )

                handle.write("\n")
                handle.flush()
                os.fsync(
                    handle.fileno()
                )

            os.replace(
                temp_name,
                self.profile_file,
            )

        finally:
            temp_path = Path(temp_name)

            if temp_path.exists():
                temp_path.unlink()

    # ============================================================
    # PROFILE SELECTION
    # ============================================================

    def select_profile(self, index):
        index = int(index)

        if not 0 <= index < len(
            self.profiles
        ):
            raise IndexError(
                f"Profile index out of range: {index}"
            )

        self.current_index = index
        self.save()

        profile = self.current_profile

        print(
            f"[CyberDaemon] Profile selected: "
            f"{profile.name}"
        )

        return profile

    def next_profile(self):
        if not self.profiles:
            raise RuntimeError(
                "No profiles available."
            )

        self.current_index = (
            self.current_index + 1
        ) % len(self.profiles)

        self.save()

        profile = self.current_profile

        print(
            f"[CyberDaemon] Profile switched: "
            f"{profile.name}"
        )

        return profile

    # ============================================================
    # PROFILE MANAGEMENT
    # ============================================================

    def add_profile(self, profile):
        if not isinstance(
            profile,
            Profile,
        ):
            raise TypeError(
                "profile must be a Profile instance."
            )

        self.profiles.append(profile)
        self.save()

        return profile

    def create_profile(
        self,
        name,
        source_profile=None,
    ):
        """Create a new profile.

        If source_profile is supplied, make a complete copy of it.
        Otherwise use clean defaults.
        """

        clean_name = (
            str(name).strip()
            or "New Profile"
        )

        if source_profile is None:
            profile = Profile(
                name=clean_name
            )

        else:
            if not isinstance(
                source_profile,
                Profile,
            ):
                raise TypeError(
                    "source_profile must be a Profile instance."
                )

            profile = Profile(
                name=clean_name,
                eq=EQSettings(
                    preset=source_profile.eq.preset,
                    bands=list(
                        source_profile.eq.bands
                    ),
                ),
                sidetone=source_profile.sidetone,
                rgb=RGBSettings(
                    effect=source_profile.rgb.effect,
                    color=source_profile.rgb.color,
                    brightness=source_profile.rgb.brightness,
                ),
                surround=SurroundSettings(
                    enabled=source_profile.surround.enabled
                ),
            )

        self.profiles.append(profile)

        self.current_index = (
            len(self.profiles) - 1
        )

        self.save()

        print(
            f"[CyberDaemon] Profile created: "
            f"{profile.name}"
        )

        return profile

    def rename_profile(
        self,
        index,
        name,
    ):
        index = int(index)

        if not 0 <= index < len(
            self.profiles
        ):
            raise IndexError(
                f"Profile index out of range: {index}"
            )

        clean_name = str(name).strip()

        if not clean_name:
            raise ValueError(
                "Profile name cannot be empty."
            )

        self.profiles[index].name = (
            clean_name
        )

        self.save()

        return self.profiles[index]

    def delete_profile(self, index):
        index = int(index)

        if not 0 <= index < len(
            self.profiles
        ):
            raise IndexError(
                f"Profile index out of range: {index}"
            )

        if len(self.profiles) <= 1:
            raise ValueError(
                "At least one profile must remain."
            )

        deleted = self.profiles.pop(index)

        if self.current_index >= len(
            self.profiles
        ):
            self.current_index = (
                len(self.profiles) - 1
            )

        elif index < self.current_index:
            self.current_index -= 1

        self.save()

        print(
            f"[CyberDaemon] Profile deleted: "
            f"{deleted.name}"
        )

        return deleted

    # ============================================================
    # UPDATE / PERSIST
    # ============================================================

    def save_current_profile(self):
        self.save()

    def update_current(
        self,
        *,
        name=None,
        eq=None,
        sidetone=None,
        rgb=None,
        surround=None,
    ):
        profile = self.current_profile

        if name is not None:
            clean_name = str(name).strip()

            if clean_name:
                profile.name = clean_name

        if eq is not None:
            if not isinstance(
                eq,
                EQSettings,
            ):
                raise TypeError(
                    "eq must be an EQSettings instance."
                )

            profile.eq = eq

        if sidetone is not None:
            profile.sidetone = max(
                0,
                min(
                    100,
                    int(sidetone),
                ),
            )

        if rgb is not None:
            if not isinstance(
                rgb,
                RGBSettings,
            ):
                raise TypeError(
                    "rgb must be an RGBSettings instance."
                )

            rgb.brightness = max(
                0,
                min(
                    100,
                    int(rgb.brightness),
                ),
            )

            profile.rgb = rgb

        if surround is not None:
            if isinstance(
                surround,
                SurroundSettings,
            ):
                profile.surround = surround

            else:
                profile.surround = (
                    SurroundSettings(
                        enabled=bool(
                            surround
                        )
                    )
                )

        self.save()

        return profile

    def update_eq(
        self,
        *,
        preset=None,
        bands=None,
    ):
        profile = self.current_profile

        if preset is not None:
            profile.eq.preset = str(
                preset
            )

        if bands is not None:
            values = []

            for value in list(
                bands
            )[:10]:
                try:
                    values.append(
                        float(value)
                    )
                except (
                    TypeError,
                    ValueError,
                ):
                    values.append(
                        0.0
                    )

            values += [
                0.0
            ] * (
                10 - len(values)
            )

            profile.eq.bands = values

        self.save()

        return profile.eq

    def update_sidetone(
        self,
        value,
    ):
        self.current_profile.sidetone = max(
            0,
            min(
                100,
                int(value),
            ),
        )

        self.save()

        return self.current_profile.sidetone

    def update_rgb(
        self,
        *,
        effect=None,
        color=None,
        brightness=None,
    ):
        rgb = self.current_profile.rgb

        if effect is not None:
            rgb.effect = str(effect)

        if color is not None:
            rgb.color = str(color)

        if brightness is not None:
            rgb.brightness = max(
                0,
                min(
                    100,
                    int(brightness),
                ),
            )

        self.save()

        return rgb

    def update_surround(
        self,
        enabled,
    ):
        """Update 7.1 state of the active profile and save."""

        self.current_profile.surround.enabled = (
            bool(enabled)
        )

        self.save()

        return (
            self.current_profile.surround.enabled
        )
