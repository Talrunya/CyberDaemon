import os
import sys
from pathlib import Path

from PySide6.QtWidgets import QApplication

from ui.main_window import MainWindow


AUTOSTART_FILE = (
    Path.home()
    / ".config"
    / "autostart"
    / "cyberdaemon.desktop"
)


def _install_appimage_autostart():
    """Create the per-user Linux autostart entry for an AppImage."""

    appimage = os.environ.get("APPIMAGE")

    if not appimage:
        return

    appimage_path = Path(
        appimage
    ).expanduser().resolve()

    if not appimage_path.exists():
        return

    AUTOSTART_FILE.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    desktop_entry = (
        "[Desktop Entry]\n"
        "Type=Application\n"
        "Name=CyberDaemon\n"
        "Comment=CyberDaemon HS80 MAX control\n"
        f'Exec="{appimage_path}" --tray\n'
        "Terminal=false\n"
        "StartupNotify=false\n"
        "X-GNOME-Autostart-enabled=true\n"
    )

    AUTOSTART_FILE.write_text(
        desktop_entry,
        encoding="utf-8",
    )


def _silence_appimage_output():
    """Silence stdout/stderr for normal AppImage launches."""

    if not os.environ.get("APPIMAGE"):
        return

    if os.environ.get("CYBERDAEMON_DEBUG") == "1":
        return

    devnull = open(
        os.devnull,
        "w",
        encoding="utf-8",
    )

    sys.stdout = devnull
    sys.stderr = devnull


def main():
    is_appimage = bool(
        os.environ.get("APPIMAGE")
    )

    # The first manual AppImage launch creates/updates the per-user
    # autostart entry. The entry itself launches the same AppImage with
    # --tray on future desktop logins.
    _install_appimage_autostart()

    _silence_appimage_output()

    app = QApplication(sys.argv)

    # Keep CyberDaemon alive while the editor is hidden in the tray.
    app.setQuitOnLastWindowClosed(False)

    window = MainWindow()

    # AppImage is a tray application by default. This applies both to
    # autostart and to a user double-clicking the AppImage manually.
    # Development Python launches remain visible for easier testing.
    if is_appimage or "--tray" in sys.argv:
        window.hide()
    else:
        window.show()

    sys.exit(app.exec())



if __name__ == "__main__":
    main()
