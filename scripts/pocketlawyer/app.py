import sys

from PyQt6.QtCore import QSize, Qt
from PyQt6.QtGui import QKeySequence, QShortcut
from PyQt6.QtWidgets import (QApplication, QButtonGroup, QHBoxLayout, QLabel, QMainWindow,
                             QPushButton, QStackedWidget, QVBoxLayout, QWidget)

from .backend import Config, make_engine
from .pages import AskPage, LibraryPage, SearchPage, SettingsPage
from . import icons
from .theme import colors, style


class MainWindow(QMainWindow):
    def __init__(self, cfg):
        super().__init__()
        self.cfg = cfg
        self.engine = make_engine(cfg)
        self.setWindowTitle("Pocket Lawyer")
        self.setWindowIcon(icons.app_icon())
        self.resize(1100, 720)

        root = QWidget()
        root.setObjectName("root")
        h = QHBoxLayout(root)
        h.setContentsMargins(0, 0, 0, 0)
        h.setSpacing(0)

        side = QWidget()
        side.setObjectName("sidebar")
        side.setFixedWidth(210)
        sl = QVBoxLayout(side)
        sl.setContentsMargins(14, 18, 14, 14)
        sl.setSpacing(4)
        brand = QLabel("Pocket Lawyer")
        brand.setObjectName("brand")
        sub = QLabel("Private policy assistant")
        sub.setObjectName("brandSub")
        sl.addWidget(brand)
        sl.addWidget(sub)
        sl.addSpacing(16)

        self.stack = QStackedWidget()
        self.ask = AskPage(lambda: self.engine, lambda: self.cfg)
        self.search = SearchPage(lambda: self.engine)
        self.library = LibraryPage(lambda: self.engine)
        self.settings = SettingsPage(cfg, lambda: self.engine)

        self.nav = []
        group = QButtonGroup(self)
        group.setExclusive(True)
        for i, (name, page) in enumerate([("Ask", self.ask), ("Search", self.search),
                                          ("Library", self.library), ("Settings", self.settings)]):
            self.stack.addWidget(page)
            b = QPushButton(name)
            b.setObjectName("nav")
            b.setCheckable(True)
            b.setIconSize(QSize(20, 20))
            self.nav.append((name.lower(), b))
            b.setCursor(Qt.CursorShape.PointingHandCursor)
            b.clicked.connect(lambda _=False, idx=i: self._go(idx))
            group.addButton(b)
            sl.addWidget(b)
            if i == 0:
                b.setChecked(True)
        sl.addStretch()
        self.mode = QLabel("")
        self.mode.setObjectName("muted")
        sl.addWidget(self.mode)

        h.addWidget(side)
        h.addWidget(self.stack, 1)
        self.setCentralWidget(root)

        sb = self.statusBar()
        self.state = QLabel("Ready")
        self.speed = QLabel("")
        self.model_lbl = QLabel("")
        sb.addWidget(self.state, 1)
        sb.addPermanentWidget(self.speed)
        sb.addPermanentWidget(self.model_lbl)

        self.ask.status_changed.connect(self.state.setText)
        self.ask.speed_changed.connect(self.speed.setText)
        self.library.documents_loaded.connect(self.search.set_documents)
        self.settings.saved.connect(self._config_changed)
        self.library.rows_loaded.connect(self.ask.set_stats)
        self.ask.open_library.connect(lambda: self._select(2))
        QShortcut(QKeySequence("Ctrl+N"), self, self.ask.new_chat)
        QShortcut(QKeySequence("Escape"), self, lambda: self.ask.worker and self.ask.worker.cancel())
        self.apply_theme(cfg.theme)
        self._config_changed()

    def _nav_icons(self):
        c = colors(self.cfg.theme)
        for name, b in self.nav:
            b.setIcon(icons.nav_icon(name, c["MUTED"], c["ACCENT_HI"]))

    def apply_theme(self, name):
        QApplication.instance().setStyleSheet(style(name))
        self._nav_icons()

    def _select(self, idx):
        self.nav[idx][1].setChecked(True)
        self._go(idx)

    def _go(self, idx):
        self.stack.setCurrentIndex(idx)
        if idx == 2:
            self.library.refresh()

    def _config_changed(self):
        self.engine = make_engine(self.cfg)
        self.apply_theme(self.cfg.theme)
        self.library.refresh()
        self.model_lbl.setText(f"Model: {self.cfg.model}")
        self.mode.setText("Demo mode" if self.cfg.demo else "Live: " + self.cfg.root)


def main():
    cfg = Config.load()
    args = sys.argv[1:]
    if "--demo" in args:
        cfg.demo = True
    if "--root" in args:
        cfg.root = args[args.index("--root") + 1]
    app = QApplication(sys.argv)
    if sys.platform == "win32":
        try:
            import ctypes
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("PocketLawyer.App")
        except Exception:
            pass
    app.setWindowIcon(icons.app_icon())
    app.setStyleSheet(style(cfg.theme))
    win = MainWindow(cfg)
    win.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
