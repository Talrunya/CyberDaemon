from PySide6.QtCore import Qt, QSize, QTimer
from PySide6.QtGui import QColor
from PySide6.QtGui import QIcon, QPixmap
from PySide6.QtSvgWidgets import QSvgWidget
from PySide6.QtWidgets import (
    QApplication,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QPushButton,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
    QMenu,
    QSystemTrayIcon,
)

from hardware.profiles import ProfileManager
from hardware.worker import HardwareWorker
from hardware.pipewire_eq import PipeWireEQ
from hardware.pipewire_surround import PipeWireSurround
from hardware.firmware import FirmwareManager
from hardware.sidetone import SidetonePage
from .overview import OverviewPage
from .cyberdaemon_logo import asset
from .lighting import LightingPage
from .equalizer import EqualizerPage
from .profiles_page import ProfilesPage
from hardware.sidetone import SidetonePage
from hardware.settings import SettingsPage
from .theme import (
    CYAN,
    GREEN,
    MAGENTA,
    TEXT_SECONDARY,
    apply_theme,
)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("CyberDaemon // HS80 MAX")
        self.setWindowIcon(
            QIcon(str(asset("cyberdaemon_emblem.png")))
        )
        self.resize(1200, 850)
        self.setMinimumSize(1000, 730)

        self._quitting = False

        apply_theme(QApplication.instance())

        self.pages = {}
        self.nav_buttons = {}

        self.hardware_worker = None
        self.profile_manager = ProfileManager()
        self.pipewire_eq = PipeWireEQ()
        self.pipewire_surround = PipeWireSurround()

        self.firmware_manager = FirmwareManager()

        self._firmware_check_timer = QTimer(self)
        self._firmware_check_timer.setInterval(
            60 * 60 * 1000
        )
        self._firmware_check_timer.timeout.connect(
            self._automatic_firmware_check
        )
        self._firmware_check_timer.start()

        self._setup_tray()

        self._build_ui()
        self._start_hardware_worker()
        self._show_page("Overview")

        # Show the officially documented HS80 MAX receiver target immediately.
        settings_page = self.pages.get("Settings")
        if settings_page is not None:
            known = self.firmware_manager.known_latest_versions()
            receiver_latest = known.get("receiver")
            if receiver_latest:
                settings_page.set_firmware_versions(
                    receiver_latest=receiver_latest
                )

    # ========================================================
    # SYSTEM TRAY
    # ========================================================

    def _setup_tray(self):
        """Create the CyberDaemon system tray icon and menu."""

        self.tray_icon = QSystemTrayIcon(
            self.windowIcon(),
            self,
        )

        self.tray_icon.setToolTip(
            "CyberDaemon // HS80 MAX"
        )

        menu = QMenu(self)

        open_action = menu.addAction(
            "OPEN CYBERDAEMON"
        )
        open_action.triggered.connect(
            self._show_from_tray
        )

        menu.addSeparator()

        quit_action = menu.addAction(
            "EXIT CYBERDAEMON"
        )
        quit_action.triggered.connect(
            self._quit_from_tray
        )

        self.tray_icon.setContextMenu(menu)

        self.tray_icon.activated.connect(
            self._tray_activated
        )

        self.tray_icon.show()

    def _show_from_tray(self):
        """Restore the editor window."""

        self.showNormal()
        self.raise_()
        self.activateWindow()

    def _tray_activated(self, reason):
        """Open the editor from the system tray."""

        if reason == QSystemTrayIcon.Trigger:
            self._show_from_tray()

    def _quit_from_tray(self):
        """Actually terminate CyberDaemon and leave no process behind."""

        self._quitting = True

        if hasattr(self, "tray_icon"):
            self.tray_icon.hide()

        # With setQuitOnLastWindowClosed(False), closing the main window
        # alone does NOT terminate QApplication. Explicitly quit the
        # event loop after the normal closeEvent shutdown path.
        self.close()

        app = QApplication.instance()
        if app is not None:
            app.quit()

    def _notify_profile_switch(self, profile_name):
        """Show a short native notification for wheel profile changes."""

        if not hasattr(self, "tray_icon"):
            return

        self.tray_icon.showMessage(
            "CYBERDAEMON",
            f"PROFILE SWITCHED TO // {profile_name.upper()}",
            QSystemTrayIcon.Information,
            1600,
        )

    # ========================================================
    # HARDWARE
    # ========================================================

    def _start_hardware_worker(self):
        """Start background HS80 MAX hardware polling."""

        self.hardware_worker = HardwareWorker(self)

        self.hardware_worker.status_updated.connect(
            self._hardware_status_updated
        )

        self.hardware_worker.connection_changed.connect(
            self._hardware_connection_changed
        )

        self.hardware_worker.error.connect(
            self._hardware_error
        )

        self.hardware_worker.listener_data.connect(
            self._hardware_listener_data
        )

        if hasattr(self.hardware_worker, "volume_changed"):
            self.hardware_worker.volume_changed.connect(
                self._volume_changed
            )

        lighting_page = self.pages.get("Lighting")

        if lighting_page is not None:
            lighting_page.rgb_apply_requested.connect(
                self._lighting_apply_requested
            )
        sidetone_page = self.pages.get("Sidetone")

        if sidetone_page is not None:
            sidetone_page.sidetone_apply_requested.connect(
                self.hardware_worker.set_sidetone
            )
        settings_page = self.pages.get("Settings")

        if settings_page is not None:
            settings_page.sleep_timer_changed.connect(
                self.hardware_worker.set_sleep_timer
            )

            check_signal = getattr(
                settings_page,
                "firmware_check_requested",
                None,
            )
            if check_signal is not None:
                check_signal.connect(
                    self._manual_firmware_check
                )

            update_signal = getattr(
                settings_page,
                "firmware_update_requested",
                None,
            )
            if update_signal is not None:
                update_signal.connect(
                    self._firmware_update_requested
                )

        self.hardware_worker.start()

    def _hardware_status_updated(self, status):
        """Forward live hardware data to the overview."""

        overview = self.pages.get("Overview")

        if overview is not None:
            overview.update_status(status)

        firmware = getattr(
            status,
            "firmware",
            None,
        )

        if firmware:
            self.firmware_manager.headset_info.current = str(
                firmware
            )

            settings_page = self.pages.get("Settings")
            if settings_page is not None:
                setter = getattr(
                    settings_page,
                    "set_firmware_versions",
                    None,
                )
                if callable(setter):
                    setter(
                        current=str(firmware)
                    )

    def _hardware_connection_changed(self, connected):
        """Update connection indicators."""

        overview = self.pages.get("Overview")

        if overview is not None:
            overview.set_connection_status(connected)

        if connected:
            self._set_topbar_status(
                "●  CONNECTED",
                GREEN,
            )
            self._restore_active_profile()

            # Give FirmwareManager the same live HID objects already owned
            # by HardwareWorker. No second HID connection is opened.
            self.firmware_manager.headset = (
                getattr(
                    self.hardware_worker,
                    "headset",
                    None,
                )
            )
            self.firmware_manager.receiver = (
                getattr(
                    self.hardware_worker,
                    "receiver",
                    None,
                )
            )

            settings_page = self.pages.get("Settings")

            if settings_page is not None:

                self.hardware_worker.set_sleep_timer(

                    settings_page.current_sleep_timer()

                )
        else:
            self._set_topbar_status(
                "●  DISCONNECTED",
                MAGENTA,
            )

    # ========================================================
    # FIRMWARE
    # ========================================================

    def _read_firmware_versions_live(self):
        """Read both firmware sources through the existing worker handles."""

        headset = (
            getattr(
                self.hardware_worker,
                "headset",
                None,
            )
        )
        receiver = (
            getattr(
                self.hardware_worker,
                "receiver",
                None,
            )
        )

        self.firmware_manager.headset = headset
        self.firmware_manager.receiver = receiver

        headset_version = None
        receiver_version = None

        if headset is not None:
            try:
                headset_version = headset.get_firmware()
            except Exception as exc:
                print(
                    "[CyberDaemon Firmware] Headset read failed:",
                    exc,
                )

        if receiver is not None:
            try:
                response = receiver.read_firmware()
                print(
                    "[CyberDaemon Firmware] RECEIVER RAW:",
                    (
                        response.hex(" ")
                        if response
                        else "<no data>"
                    ),
                )
                receiver_version = (
                    self.firmware_manager._parse_receiver_response(
                        response
                    )
                )
            except Exception as exc:
                print(
                    "[CyberDaemon Firmware] Receiver read failed:",
                    exc,
                )

        return (
            headset_version,
            receiver_version,
        )

    def _update_firmware_current_from_hardware(self):
        """Use the firmware value already read by HardwareWorker."""

        worker = self.hardware_worker
        headset = getattr(
            worker,
            "headset",
            None,
        )

        if headset is None:
            return None

        version = getattr(
            headset.status,
            "firmware",
            None,
        )

        if version:
            self.firmware_manager.headset_info.current = str(
                version
            )

        return version

    def _manual_firmware_check(self):
        """Handle the Settings manual firmware check."""

        current = (
            self._update_firmware_current_from_hardware()
        )

        headset_current, receiver_current = (
            self._read_firmware_versions_live()
        )

        if headset_current:
            current = headset_current

        settings_page = self.pages.get("Settings")

        if settings_page is not None:
            settings_page.set_firmware_versions(
                current=(
                    str(current)
                    if current
                    else None
                ),
                receiver_current=(
                    str(receiver_current)
                    if receiver_current
                    else None
                ),
            )

        if receiver_current:
            self.firmware_manager.receiver_info.current = str(
                receiver_current
            )

        known = self.firmware_manager.known_latest_versions()

        # Official receiver target only; headset latest remains unavailable
        # until the actual Corsair metadata source is identified.
        result = self.firmware_manager.check_for_updates(
            headset_latest=None,
            receiver_latest=known.get("receiver"),
        )

        if settings_page is not None:
            headset_info, receiver_info = result

            settings_page.set_firmware_versions(
                current=str(current) if current else None,
                receiver_latest=receiver_info.latest,
            )

            headset_status = (
                "LATEST SOURCE PENDING"
                if headset_info.latest is None
                else headset_info.status
            )

            receiver_status = receiver_info.status

            settings_page.set_firmware_status(
                headset_status,
                receiver_status,
            )

            settings_page.finish_firmware_check(
                True,
                (
                    "CHECK COMPLETE // "
                    f"RECEIVER {receiver_status}"
                ),
            )

    def _automatic_firmware_check(self):
        """Run the scheduled 12-hour check hook."""

        if not self.firmware_manager.automatic_check_due():
            return

        current = (
            self._update_firmware_current_from_hardware()
        )

        settings_page = self.pages.get("Settings")

        if settings_page is not None and current:
            settings_page.set_firmware_versions(
                current=str(current)
            )

        known = self.firmware_manager.known_latest_versions()

        self.firmware_manager.check_for_updates(
            headset_latest=None,
            receiver_latest=known.get("receiver"),
        )

        self.firmware_manager.mark_automatic_check()

        # Notify only when the comparison establishes an actual update.
        for component, latest in (
            self.firmware_manager.get_new_update_notifications()
        ):
            if hasattr(self, "tray_icon"):
                self.tray_icon.showMessage(
                    "CYBERDAEMON",
                    (
                        f"NEW FIRMWARE AVAILABLE // "
                        f"{component} {latest}"
                    ),
                    QSystemTrayIcon.Information,
                    5000,
                )

    def _firmware_update_requested(
        self,
        current_version,
        latest_version,
    ):
        """Safe placeholder until the real Corsair flasher is ready."""

        del current_version
        del latest_version

        settings_page = self.pages.get("Settings")
        if settings_page is not None:
            settings_page.finish_firmware_update(
                False,
                "FLASHER NOT READY",
            )

    def _volume_changed(self, value):
        """Forward live system volume changes to the overview."""
        overview = self.pages.get("Overview")
        if overview is None:
            return

        setter = getattr(overview, "set_volume", None)
        if callable(setter):
            setter(int(value))
        else:
            # Current Overview already polls PipeWire every 250 ms.
            # Trigger an immediate refresh when the worker changes volume.
            refresh = getattr(overview, "update_system_volume", None)
            if callable(refresh):
                refresh()

    def _restore_active_profile(self):
        profile = self.profile_manager.current_profile
        print(
            "[CyberDaemon] Restoring active profile:",
            profile.name,
        )
        self._load_profile_everywhere(profile, apply_hardware=True)

    def _load_profile_everywhere(self, profile, apply_hardware=True):
        equalizer_page = self.pages.get("Equalizer")
        if equalizer_page is not None:
            loader = getattr(equalizer_page, "load_profile", None)
            if callable(loader):
                loader(profile)
        sidetone_page = self.pages.get("Sidetone")
        if sidetone_page is not None:
            loader = getattr(sidetone_page, "load_profile", None)
            if callable(loader):
                loader(profile)
        lighting_page = self.pages.get("Lighting")
        if lighting_page is not None:
            lighting_page.load_profile(profile)

        profiles_page = self.pages.get("Profiles")
        if profiles_page is not None:
            refresh = getattr(profiles_page, "refresh_profiles", None)
            if callable(refresh):
                refresh(select_current=True)
            editor = getattr(profiles_page, "_load_profile_into_editor", None)
            if callable(editor):
                editor(profile)
                sidetone_page = self.pages.get("Sidetone")

        if sidetone_page is not None:
            loader = getattr(
                sidetone_page,
                "load_profile",
                None,
            )

            if callable(loader):
                loader(profile)
        self._update_profile_ui()

        # Apply the active profile's EQ through PipeWire.
        # This is deliberately independent from the HS80 hardware worker:
        # EQ is software/DSP processing, while RGB remains hardware-side.
        eq_ok = False
        try:
            if self.pipewire_eq.available():
                eq_ok = bool(
                    self.pipewire_eq.apply(profile.eq.bands)
                )
                if eq_ok:
                    print(
                        "[CyberDaemon] EQ applied:",
                        profile.name,
                        list(profile.eq.bands[:10]),
                    )
                else:
                    print(
                        "[CyberDaemon] EQ apply returned False."
                    )
            else:
                print(
                    "[CyberDaemon] EQ unavailable: "
                    "PipeWire pw-cli/pw-dump not found."
                )
        except Exception as exc:
            print(
                "[CyberDaemon] EQ apply failed:",
                exc,
            )

        self._sync_surround(
            profile,
            eq_ok=eq_ok,
        )

        if apply_hardware and self.hardware_worker is not None:
            color = QColor(profile.rgb.color)
            if color.isValid():
                self._lighting_apply_requested(
                    color.red(),
                    color.green(),
                    color.blue(),
                    profile.rgb.brightness,
                    profile.rgb.effect,
                )

    def _sync_surround(self, profile, eq_ok=True):
        """Synchronize the PipeWire surround chain with the profile state."""
        enabled = bool(
            getattr(
                getattr(profile, "surround", None),
                "enabled",
                False,
            )
        )

        if not enabled:
            if self.pipewire_surround.active:
                self.pipewire_surround.stop()

            if eq_ok:
                if not self.pipewire_eq.set_default():
                    print(
                        "[CyberDaemon] Could not restore EQ as default sink."
                    )
            return True

        if not eq_ok:
            print(
                "[CyberDaemon] Surround not started: EQ chain is not active."
            )
            self.pipewire_surround.stop()
            return False

        try:
            if self.pipewire_surround.active:
                ok = self.pipewire_surround.ensure_target(
                    self.pipewire_eq.NODE_NAME
                )
            else:
                ok = self.pipewire_surround.start(
                    target_sink=self.pipewire_eq.NODE_NAME
                )
        except Exception as exc:
            print(
                "[CyberDaemon] Surround apply failed:",
                exc,
            )
            ok = False

        if ok:
            print(
                "[CyberDaemon] 7.1 Surround active through EQ."
            )
        else:
            print(
                "[CyberDaemon] 7.1 Surround could not be activated."
            )

        return ok

    def _surround_changed(self, profile, enabled):
        """Apply a live surround toggle from the Profiles page."""
        profiles_page = self.pages.get("Profiles")
        if profiles_page is None:
            return

        if profile is None:
            return

        # Editing a non-active profile only changes its saved state.
        # Audio routing is changed when that profile becomes active.
        try:
            is_active = (
                self.profile_manager.profiles.index(profile)
                == self.profile_manager.current_index
            )
        except ValueError:
            return

        if not is_active:
            return

        if enabled:
            # Make sure the current EQ graph exists before routing
            # the 7.1 result into it. Live EQ updates remain untouched.
            eq_ok = bool(
                self.pipewire_eq.available()
                and self.pipewire_eq.apply(profile.eq.bands)
            )

            if not self._sync_surround(profile, eq_ok=eq_ok):
                profiles_page.set_surround_enabled(
                    False,
                    save=True,
                )
            return

        self._sync_surround(
            profile,
            eq_ok=True,
        )

    def _hardware_error(self, message):
        """Handle hardware errors."""

        print(f"[CyberDaemon] Hardware error: {message}")

        self._set_topbar_status(
            "●  ERROR",
            MAGENTA,
        )

    def _lighting_apply_requested(
        self,
        red,
        green,
        blue,
        brightness,
        effect,
    ):
        """Queue the selected lighting state for the HS80 MAX."""

        print(
            "[CyberDaemon] Lighting apply requested:",
            f"R={red}",
            f"G={green}",
            f"B={blue}",
            f"Brightness={brightness}",
            f"Effect={effect}",
        )

        if self.hardware_worker is None:
            print(
                "[CyberDaemon] Lighting apply failed: "
                "hardware worker is not available."
            )
            return

        if not self.hardware_worker.isRunning():
            print(
                "[CyberDaemon] Lighting apply failed: "
                "hardware worker is not running."
            )
            return

        self.hardware_worker.apply_rgb(
            red,
            green,
            blue,
            brightness,
            effect,
        )

    def _hardware_listener_data(self, data):
        """Handle asynchronous HS80 MAX hardware events."""

        if len(data) < 4:
            return

        # ----------------------------------------------------
        # Scroll wheel press
        # ----------------------------------------------------
        #
        # HS80 MAX:
        #   03 01 02 01 ... = press
        #   03 01 02 00 ... = release
        #
        # Only react to the press.
        #

        if (
            data[0] == 0x03
            and data[1] == 0x01
            and data[2] == 0x02
            and data[3] == 0x01
        ):
            profile = self.profile_manager.next_profile()

            print(
                f"[CyberDaemon] Active profile: "
                f"{profile.name}"
            )

            self._notify_profile_switch(
                profile.name
            )

            self._load_profile_everywhere(
                profile,
                apply_hardware=True,
            )

    # ========================================================
    # UI
    # ========================================================

    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)

        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        main_layout.addWidget(
            self._create_topbar()
        )

        body = QHBoxLayout()
        body.setContentsMargins(0, 0, 0, 0)
        body.setSpacing(0)

        body.addWidget(
            self._create_sidebar()
        )

        self.stack = QStackedWidget()
        body.addWidget(
            self.stack,
            1,
        )

        main_layout.addLayout(
            body,
            1,
        )

        self._create_pages()

    # ========================================================
    # TOP BAR
    # ========================================================

    def _create_topbar(self):
        frame = QFrame()
        frame.setObjectName("topbar")
        frame.setFixedHeight(84)

        layout = QHBoxLayout(frame)
        layout.setContentsMargins(
            24,
            0,
            24,
            0,
        )

        brand = QLabel()
        brand.setObjectName("brand")
        brand.setFixedSize(330, 72)
        brand.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        brand_pixmap = QPixmap(str(asset("cyberdaemon_wordmark.png")))
        if not brand_pixmap.isNull():
            brand.setPixmap(
                brand_pixmap.scaled(
                    325,
                    72,
                    Qt.KeepAspectRatio,
                    Qt.SmoothTransformation,
                )
            )

        separator = QLabel("//")
        separator.setStyleSheet(
            f"color: {MAGENTA}; "
            "font-size: 13px; "
            "font-weight: 700;"
        )

        device = QLabel("HS80 MAX")
        device.setStyleSheet(
            f"color: {TEXT_SECONDARY}; "
            "font-size: 16px; "
            "font-weight: 800;"
            "letter-spacing: 1px;"
        )

        layout.addWidget(brand)
        layout.addSpacing(10)
        layout.addWidget(separator)
        layout.addSpacing(10)
        layout.addWidget(device)

        layout.addStretch()

        self.topbar_status = QLabel(
            "●  CHECKING"
        )
        self.topbar_status.setStyleSheet(
            f"color: {CYAN}; "
            "font-size: 10px; "
            "font-weight: 800;"
        )

        receiver = QLabel("USB RECEIVER")
        receiver.setStyleSheet(
            f"color: {CYAN}; "
            "font-size: 10px; "
            "font-weight: 700;"
        )

        layout.addWidget(
            self.topbar_status
        )
        layout.addSpacing(24)
        layout.addWidget(receiver)

        return frame

    def _set_topbar_status(self, text, color):
        self.topbar_status.setText(text)

        self.topbar_status.setStyleSheet(
            f"color: {color}; "
            "font-size: 10px; "
            "font-weight: 800;"
        )

    # ========================================================
    # SIDEBAR
    # ========================================================

    def _create_sidebar(self):
        sidebar = QFrame()
        sidebar.setObjectName("sidebar")
        sidebar.setFixedWidth(210)

        layout = QVBoxLayout(sidebar)
        layout.setContentsMargins(
            14,
            20,
            10,
            20,
        )
        layout.setSpacing(3)

        self._add_section(
            layout,
            "SYSTEM",
        )

        self._add_nav(
            layout,
            "Overview",
            "OVERVIEW",
        )

        self._add_section(
            layout,
            "AUDIO",
        )

        self._add_nav(
            layout,
            "Equalizer",
            "EQUALIZER",
        )

        self._add_nav(
            layout,
            "Sidetone",
            "SIDETONE",
        )

        self._add_section(
            layout,
            "LIGHTING",
        )

        self._add_nav(
            layout,
            "Lighting",
            "LIGHTING",
        )

        self._add_section(
            layout,
            "INPUT",
        )

        self._add_nav(

            layout,

            "Settings",

            "SETTINGS",

        )

        self._add_section(
            layout,
            "PROFILES",
        )

        self._add_nav(
            layout,
            "Profiles",
            "PROFILES",
        )

        layout.addStretch()

        footer_row = QHBoxLayout()
        footer_row.setSpacing(7)

        tux = QSvgWidget(str(asset("linux_tux.svg")))
        tux.setFixedSize(24, 24)

        footer = QLabel(
            "CYBERDAEMON // LINUX"
            "<br>"
            "© 2026 Talrunya"
        )

        footer.setStyleSheet(
            f"color: {TEXT_SECONDARY}; "
            "font-size: 9px; "
            "font-weight: 700;"
        )

        footer_row.addWidget(tux)
        footer_row.addWidget(footer)
        footer_row.addStretch()
        layout.addLayout(footer_row)

        return sidebar

    def _add_section(self, layout, title):
        label = QLabel(title)

        label.setObjectName(
            "eyebrow"
        )

        label.setContentsMargins(
            4,
            10,
            0,
            4,
        )

        layout.addWidget(label)

    def _add_nav(
        self,
        layout,
        page_name,
        text,
    ):
        button = QPushButton(text)

        icon_name = {
            "Overview": "icon_overview.svg",
            "Equalizer": "icon_equalizer.svg",
            "Sidetone": "icon_sidetone.svg",
            "Lighting": "icon_lighting.svg",
            "Settings": "icon_settings.svg",
            "Profiles": "icon_profiles.svg",
        }.get(page_name)

        if icon_name:
            button.setIcon(QIcon(str(asset(icon_name))))
            button.setIconSize(QSize(22, 22))

        button.setObjectName("nav")
        button.setCheckable(True)
        button.setCursor(
            Qt.PointingHandCursor
        )

        button.clicked.connect(
            lambda checked=False,
            name=page_name:
            self._show_page(name)
        )

        layout.addWidget(button)

        self.nav_buttons[
            page_name
        ] = button

    # ========================================================
    # PAGES
    # ========================================================

    def _create_pages(self):
        # ----------------------------------------------------
        # Overview
        # ----------------------------------------------------
        overview = OverviewPage()
        self.pages["Overview"] = overview
        self.stack.addWidget(overview)

        # ----------------------------------------------------
        # Equalizer
        # ----------------------------------------------------
        equalizer = EqualizerPage(
            profile_manager=self.profile_manager
        )
        self.pages["Equalizer"] = equalizer
        self.stack.addWidget(equalizer)

        # ----------------------------------------------------
        # Sidetone / Microphone / Buttons
        # ----------------------------------------------------
        # ----------------------------------------------------
      
        sidetone_page = SidetonePage(
            profile_manager=self.profile_manager
        )

        self.pages["Sidetone"] = sidetone_page
        self.stack.addWidget(sidetone_page)

        # ----------------------------------------------------
        # Settings
        # ----------------------------------------------------
        settings_page = SettingsPage()
        self.pages["Settings"] = settings_page
        self.stack.addWidget(settings_page)

        

        # ----------------------------------------------------
        # Lighting
        # ----------------------------------------------------
        lighting_page = LightingPage(
            profile_manager=self.profile_manager
        )
        self.pages["Lighting"] = lighting_page
        self.stack.addWidget(lighting_page)

        # ----------------------------------------------------
        # Profiles
        # ----------------------------------------------------
        profiles_page = ProfilesPage(
            profile_manager=self.profile_manager
        )
        self.pages["Profiles"] = profiles_page
        self.stack.addWidget(profiles_page)

        profiles_page.profile_activated.connect(
            self._profile_page_activated
        )
        profiles_page.surround_changed.connect(
            self._surround_changed
        )

    def _create_placeholder_page(
        self,
        title,
        subtitle,
    ):
        page = QWidget()

        layout = QVBoxLayout(page)

        layout.setContentsMargins(
            30,
            28,
            30,
            28,
        )

        layout.setSpacing(8)

        title_label = QLabel(title)
        title_label.setObjectName(
            "pageTitle"
        )

        subtitle_label = QLabel(
            subtitle
        )

        subtitle_label.setObjectName(
            "eyebrow"
        )

        layout.addWidget(
            title_label
        )

        layout.addWidget(
            subtitle_label
        )

        layout.addSpacing(20)

        card = QFrame()
        card.setObjectName("card")

        card_layout = QVBoxLayout(card)

        card_layout.setContentsMargins(
            22,
            22,
            22,
            22,
        )

        ready = QLabel(
            "MODULE READY"
        )

        ready.setObjectName(
            "eyebrow"
        )

        description = QLabel(
            "Dieses Modul ist vorbereitet.\n\n"
            "Die eigentliche Hardware-Funktion "
            "wird später separat angebunden."
        )

        description.setStyleSheet(
            "font-size: 14px; "
            "font-weight: 600;"
        )

        card_layout.addWidget(
            ready
        )

        card_layout.addSpacing(8)

        card_layout.addWidget(
            description
        )

        card_layout.addStretch()

        layout.addWidget(
            card,
            1,
        )

        return page

    # ========================================================
    # PROFILES
    # ========================================================

    def _update_profile_ui(self):
        """Refresh the active profile indicator if the page provides one."""
        page = self.pages.get("Profiles")
        if page is None:
            return

        updater = getattr(page, "update_active_profile", None)
        if callable(updater):
            updater()

    # ========================================================
    # PROFILE SYNCHRONIZATION
    # ========================================================

    def _profile_page_activated(self, profile):
        print(
            f"[CyberDaemon] Profile page selected: {profile.name}"
        )
        self._load_profile_everywhere(
            profile,
            apply_hardware=True,
        )

    # ========================================================
    # NAVIGATION
    # ========================================================

    def _show_page(self, page_name):
        page = self.pages.get(
            page_name
        )

        if page is None:
            return

        self.stack.setCurrentWidget(
            page
        )

        for name, button in (
            self.nav_buttons.items()
        ):
            button.setChecked(
                name == page_name
            )

    # ========================================================
    # SHUTDOWN
    # ========================================================

    def closeEvent(self, event):
        """Hide to tray unless the user explicitly chose EXIT."""

        if not self._quitting:
            self.hide()
            self.tray_icon.show()
            event.ignore()
            return

        if (
            self.hardware_worker
            is not None
        ):
            self.hardware_worker.stop()

        try:
            self.pipewire_surround.stop()
        except Exception as exc:
            print(
                "[CyberDaemon] Surround shutdown warning:",
                exc,
            )

        try:
            self.pipewire_eq.stop()
        except Exception as exc:
            print(
                "[CyberDaemon] EQ shutdown warning:",
                exc,
            )

        event.accept()


def create_window():
    return MainWindow()