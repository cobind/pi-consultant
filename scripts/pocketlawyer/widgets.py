from PyQt6.QtCore import Qt, QTimer, QUrl
from PyQt6.QtGui import QDesktopServices
from PyQt6.QtWidgets import (QFrame, QHBoxLayout, QLabel, QPushButton, QScrollArea,
                             QVBoxLayout, QWidget)

from . import theme


def _label(text="", wrap=True, selectable=True, name=None):
    lab = QLabel(text)
    lab.setWordWrap(wrap)
    if name:
        lab.setObjectName(name)
    if selectable:
        lab.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
    return lab


class Bubble(QFrame):

    def __init__(self, role, text=""):
        super().__init__()
        self.role = role
        self.setObjectName({"user": "userBubble", "ai": "aiBubble", "error": "errBubble"}[role])
        self.setMaximumWidth(760)
        self.setMinimumWidth(460 if role != "user" else 0)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(14, 10, 14, 10)
        lay.setSpacing(6)
        self.label = _label()
        if role == "ai":
            self.label.setTextFormat(Qt.TextFormat.MarkdownText)
            self.label.setOpenExternalLinks(True)
        else:
            self.label.setTextFormat(Qt.TextFormat.PlainText)
        if role == "error":
            self.label.setStyleSheet(f"color: {theme.current()['ERR']};")
        lay.addWidget(self.label)
        self.extra = QVBoxLayout()
        self.extra.setSpacing(6)
        lay.addLayout(self.extra)
        self._dots = 0
        self._timer = QTimer(self)
        self._timer.setInterval(350)
        self._timer.timeout.connect(self._tick)
        self.set_text(text)

    def _tick(self):
        self._dots = (self._dots + 1) % 4
        self.label.setText("●" * self._dots + "○" * (3 - self._dots) if self._dots else "○○○")

    def set_text(self, text):
        if text:
            self._timer.stop()
            self.label.setText(text)
        elif self.role == "ai":
            self.label.setText("○○○")
            self._timer.start()
        else:
            self.label.setText("")

    def text(self):
        return self.label.text()


class SourceCard(QFrame):
    SNIPPET = 220

    def __init__(self, number, hit, show_number=True):
        super().__init__()
        self.setObjectName("card")
        self.hit = hit
        self.expanded = False
        lay = QVBoxLayout(self)
        lay.setContentsMargins(12, 10, 12, 10)
        lay.setSpacing(4)

        head = QHBoxLayout()
        title = f"[{number}]  {hit.doc_name}" if show_number else hit.doc_name
        t = _label(title, wrap=False, selectable=False)
        t.setStyleSheet("font-weight: 600;")
        head.addWidget(t)
        head.addStretch()
        if hit.doc_context:
            head.addWidget(_label(hit.doc_context, False, False, "badge"))
        head.addWidget(_label(f"{hit.relevance}% match", False, False, "badge"))
        lay.addLayout(head)

        self.body = _label()
        lay.addWidget(self.body)

        foot = QHBoxLayout()
        self.toggle = QPushButton("Show more")
        self.toggle.setObjectName("link")
        self.toggle.setCursor(Qt.CursorShape.PointingHandCursor)
        self.toggle.clicked.connect(self._toggle)
        foot.addWidget(self.toggle)
        foot.addStretch()
        if hit.doc_source:
            open_btn = QPushButton("Open policy")
            open_btn.setObjectName("link")
            open_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            open_btn.clicked.connect(lambda: QDesktopServices.openUrl(QUrl(hit.doc_source)))
            foot.addWidget(open_btn)
        lay.addLayout(foot)
        self._render()

    def _render(self):
        text = self.hit.text.strip()
        long = len(text) > self.SNIPPET
        self.body.setText(text if (self.expanded or not long) else text[:self.SNIPPET].rstrip() + "...")
        self.toggle.setVisible(long)
        self.toggle.setText("Show less" if self.expanded else "Show more")

    def _toggle(self):
        self.expanded = not self.expanded
        self._render()


class SourcesSection(QWidget):

    def __init__(self, hits):
        super().__init__()
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 4, 0, 0)
        lay.setSpacing(6)
        names = []
        for h in hits:
            if h.doc_name not in names:
                names.append(h.doc_name)
        self.btn = QPushButton()
        self.btn.setObjectName("link")
        self.btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn.clicked.connect(self._toggle)
        lay.addWidget(self.btn)
        self.box = QWidget()
        bl = QVBoxLayout(self.box)
        bl.setContentsMargins(0, 0, 0, 0)
        bl.setSpacing(6)
        for i, h in enumerate(hits, 1):
            bl.addWidget(SourceCard(i, h))
        lay.addWidget(self.box)
        self.summary = f"{len(hits)} excerpts from {len(names)} polic{'y' if len(names) == 1 else 'ies'}"
        self.box.setVisible(False)
        self._sync()

    def _toggle(self):
        self.box.setVisible(not self.box.isVisible())
        self._sync()

    def _sync(self):
        arrow = "Hide" if self.box.isVisible() else "Show"
        self.btn.setText(f"{arrow} sources  ·  {self.summary}")


class ChatView(QScrollArea):
    def __init__(self):
        super().__init__()
        self.setWidgetResizable(True)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        host = QWidget()
        host.setObjectName("chatHost")
        self.col = QVBoxLayout(host)
        self.col.setContentsMargins(24, 16, 24, 16)
        self.col.setSpacing(12)
        self.col.addStretch()
        self.setWidget(host)
        self.verticalScrollBar().rangeChanged.connect(self._maybe_follow)
        self._follow = True
        self.verticalScrollBar().valueChanged.connect(self._track)

    def _track(self, value):
        bar = self.verticalScrollBar()
        self._follow = value >= bar.maximum() - 40

    def _maybe_follow(self, _min, maximum):
        if self._follow:
            self.verticalScrollBar().setValue(maximum)

    def add(self, widget, align_right=False):
        row = QHBoxLayout()
        if align_right:
            row.addStretch()
            row.addWidget(widget)
        else:
            row.addWidget(widget)
            row.addStretch()
        self.col.insertLayout(self.col.count() - 1, row)
        self._follow = True
        return widget

    def clear(self):
        while self.col.count() > 1:
            item = self.col.takeAt(0)
            self._delete(item)

    def _delete(self, item):
        if item.widget():
            item.widget().deleteLater()
        elif item.layout():
            while item.layout().count():
                self._delete(item.layout().takeAt(0))
