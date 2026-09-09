from pathlib import Path
from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import QLabel

ASSET_DIR = Path(__file__).resolve().parent / "assets"

def asset(name):
    return ASSET_DIR / name

class CyberDaemonLogo(QLabel):
    def __init__(self, size=62, parent=None):
        super().__init__(parent)
        self.setFixedSize(size, size)
        self.setAlignment(Qt.AlignCenter)
        self.setScaledContents(True)
        pixmap = QPixmap(str(asset("cyberdaemon_emblem.png")))
        if not pixmap.isNull():
            self.setPixmap(pixmap)
