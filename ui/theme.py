from PySide6.QtWidgets import QApplication


# ============================================================
# iCUE // CYBERPUNK THEME
# ============================================================

# --- Core ---------------------------------------------------

BG = "#05070A"
BG_DEEP = "#030407"

PANEL = "#0A0F14"
PANEL_2 = "#0D141B"
PANEL_HOVER = "#111C24"

# --- Neon ---------------------------------------------------

CYAN = "#00F6FF"
CYAN_DARK = "#007D86"
CYAN_GLOW = "#00AAB3"

MAGENTA = "#FF00C8"
MAGENTA_DARK = "#7A0061"

GREEN = "#00FF88"
YELLOW = "#FFD000"
RED = "#FF3158"

# --- Text ---------------------------------------------------

TEXT = "#E8FCFF"
TEXT_SECONDARY = "#88A5AE"
TEXT_MUTED = "#465A63"

# --- Structure ---------------------------------------------

BORDER = "#17313A"
BORDER_DARK = "#0D2027"
BORDER_ACTIVE = "#00A8B3"


# ============================================================
# GLOBAL STYLESHEET
# ============================================================

STYLESHEET = f"""

/* ==========================================================
   GLOBAL
   ========================================================== */

QMainWindow,
QWidget {{
    background-color: {BG};
    color: {TEXT};
    font-family: "DejaVu Sans";
    font-size: 12px;
}}

QMainWindow {{
    border: 1px solid {BORDER_DARK};
}}


/* ==========================================================
   TOP BAR
   ========================================================== */

QFrame#topbar {{
    background-color: {BG_DEEP};
    border-bottom: 1px solid {CYAN_DARK};
}}

QFrame#topbar QLabel {{
    background: transparent;
}}


/* ==========================================================
   SIDEBAR
   ========================================================== */

QFrame#sidebar {{
    background-color: #060A0E;
    border-right: 1px solid {BORDER};
}}


/* ==========================================================
   CYBERPUNK PANELS
   ========================================================== */

QFrame#card {{
    background-color: {PANEL};
    border: 1px solid {BORDER};
    border-radius: 2px;
}}

QFrame#card:hover {{
    border: 1px solid {CYAN_DARK};
    background-color: {PANEL_2};
}}


/* ==========================================================
   BRAND
   ========================================================== */

QLabel#brand {{
    color: {CYAN};
    background: transparent;
    font-size: 22px;
    font-weight: 900;
}}

QLabel#brandSub {{
    color: {MAGENTA};
    background: transparent;
    font-size: 8px;
    font-weight: 800;
    letter-spacing: 4px;
}}

QLabel#pageTitle {{
    color: {TEXT};
    background: transparent;
    font-size: 27px;
    font-weight: 800;
}}

QLabel#eyebrow {{
    color: {CYAN};
    background: transparent;
    font-size: 9px;
    font-weight: 900;
    letter-spacing: 2px;
}}

QLabel#muted {{
    color: {TEXT_SECONDARY};
    background: transparent;
    font-size: 10px;
}}

QLabel#value {{
    color: {CYAN};
    background: transparent;
    font-size: 30px;
    font-weight: 800;
}}


/* ==========================================================
   SIDEBAR NAVIGATION
   ========================================================== */

QPushButton#nav {{
    background-color: transparent;
    color: {TEXT_SECONDARY};

    border: none;
    border-left: 2px solid transparent;

    border-radius: 0px;

    text-align: left;

    padding: 12px 12px;

    font-size: 10px;
    font-weight: 800;

    letter-spacing: 1px;
}}

QPushButton#nav:hover {{
    background-color: #0B171D;
    color: {TEXT};
    border-left: 2px solid {MAGENTA_DARK};
}}

QPushButton#nav:checked {{
    background-color: #0B1A20;
    color: {CYAN};
    border-left: 2px solid {CYAN};
}}


/* ==========================================================
   NEON BUTTON
   ========================================================== */

QPushButton#neon {{
    background-color: #07151A;

    color: {CYAN};

    border: 1px solid {CYAN_DARK};
    border-radius: 2px;

    padding: 8px 16px;

    font-size: 10px;
    font-weight: 800;

    letter-spacing: 1px;
}}

QPushButton#neon:hover {{
    background-color: #0B2229;
    border: 1px solid {CYAN};
    color: {TEXT};
}}

QPushButton#neon:pressed {{
    background-color: #050C10;
    border: 1px solid {MAGENTA};
    color: {MAGENTA};
}}


/* ==========================================================
   SLIDERS
   ========================================================== */

QSlider::groove:horizontal {{
    height: 3px;

    background-color: #14252C;

    border: none;
}}

QSlider::sub-page:horizontal {{
    background-color: {CYAN_DARK};
}}

QSlider::handle:horizontal {{
    width: 13px;
    height: 13px;

    margin: -5px 0;

    background-color: {CYAN};

    border: 1px solid {TEXT};

    border-radius: 0px;
}}

QSlider::handle:horizontal:hover {{
    background-color: {MAGENTA};
}}


/* ==========================================================
   PROGRESS BAR
   ========================================================== */

QProgressBar {{
    background-color: #05090C;

    border: 1px solid {BORDER};

    border-radius: 1px;

    height: 7px;

    text-align: center;

    color: transparent;
}}

QProgressBar::chunk {{
    background-color: {CYAN};
    border-radius: 0px;
}}


/* ==========================================================
   INPUTS
   ========================================================== */

QLineEdit,
QComboBox,
QSpinBox {{
    background-color: #060B0F;

    color: {TEXT};

    border: 1px solid {BORDER};

    border-radius: 1px;

    padding: 7px;
}}

QLineEdit:hover,
QComboBox:hover,
QSpinBox:hover {{
    border: 1px solid {CYAN_DARK};
}}

QLineEdit:focus,
QComboBox:focus,
QSpinBox:focus {{
    border: 1px solid {CYAN};
}}


/* ==========================================================
   SCROLLBAR
   ========================================================== */

QScrollBar:vertical {{
    background-color: #05080B;
    width: 7px;
    margin: 0px;
}}

QScrollBar::handle:vertical {{
    background-color: {BORDER_ACTIVE};

    min-height: 30px;

    border-radius: 0px;
}}

QScrollBar::handle:vertical:hover {{
    background-color: {CYAN};
}}

QScrollBar::add-line:vertical,
QScrollBar::sub-line:vertical {{
    height: 0px;
}}


/* ==========================================================
   TOOLTIP
   ========================================================== */

QToolTip {{
    background-color: #05090C;
    color: {CYAN};
    border: 1px solid {CYAN_DARK};
    padding: 6px;
}}


/* ==========================================================
   SELECTION
   ========================================================== */

QLabel::selection {{
    background-color: {CYAN_DARK};
    color: {TEXT};
}}

"""


def apply_theme(app: QApplication) -> None:
    """Apply the global iCUE cyberpunk theme."""
    app.setStyleSheet(STYLESHEET)