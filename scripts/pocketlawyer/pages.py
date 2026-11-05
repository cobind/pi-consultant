from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (QCheckBox, QComboBox, QFormLayout, QHBoxLayout, QHeaderView, QLabel,
                             QLineEdit, QPushButton, QScrollArea, QSpinBox, QTableWidget,
                             QTableWidgetItem, QVBoxLayout, QWidget, QAbstractItemView)

from PyQt6.QtCore import QUrl
from PyQt6.QtGui import QDesktopServices
from PyQt6.QtWidgets import QDialog, QFrame, QMessageBox, QStackedWidget

from . import ingest
from .dialogs import AddDocumentDialog, run_job
from . import icons, theme
from .widgets import Bubble, ChatView, SourceCard, SourcesSection
from .workers import AnswerWorker, CallWorker, IngestWorker

def header(title, subtitle=""):
    box = QWidget()
    lay = QVBoxLayout(box)
    lay.setContentsMargins(0, 0, 0, 0)
    lay.setSpacing(2)
    t = QLabel(title)
    t.setObjectName("h1")
    lay.addWidget(t)
    if subtitle:
        s = QLabel(subtitle)
        s.setObjectName("muted")
        lay.addWidget(s)
    return box


class WelcomeView(QWidget):
    open_library = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.setObjectName("chatHost")
        lay = QVBoxLayout(self)
        lay.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lay.setSpacing(10)
        logo = QLabel()
        logo.setPixmap(icons.logo_pixmap(88))
        logo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lay.addWidget(logo)
        title = QLabel("Ask about any policy")
        title.setObjectName("welcomeTitle")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lay.addWidget(title)
        sub = QLabel("Answers come from your indexed policies and stay on this device.")
        sub.setObjectName("welcomeSub")
        sub.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lay.addWidget(sub)
        lay.addSpacing(8)
        row = QHBoxLayout()
        row.setAlignment(Qt.AlignmentFlag.AlignCenter)
        row.setSpacing(12)
        self.docs, self.chunks = StatTile("Policies"), StatTile("Chunks searchable")
        row.addWidget(self.docs)
        row.addWidget(self.chunks)
        lay.addLayout(row)
        self.hint = QLabel("Type a question below, for example: \"What is the tailgating policy?\"")
        self.hint.setObjectName("muted")
        self.hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lay.addWidget(self.hint)
        self.add_btn = QPushButton("Add your first document")
        self.add_btn.setObjectName("primary")
        self.add_btn.clicked.connect(self.open_library)
        lay.addWidget(self.add_btn, alignment=Qt.AlignmentFlag.AlignCenter)
        self.set_stats(None)

    def set_stats(self, rows):
        if rows is None:
            self.docs.set("-"); self.chunks.set("-")
            self.add_btn.setVisible(False)
            return
        self.docs.set(str(len(rows)))
        self.chunks.set(f"{sum(r[3] for r in rows):,}")
        self.add_btn.setVisible(not rows)
        self.hint.setVisible(bool(rows))


class StatTile(QFrame):
    def __init__(self, caption):
        super().__init__()
        self.setObjectName("stat")
        self.setMinimumWidth(150)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(18, 12, 18, 12)
        lay.setSpacing(0)
        self.num = QLabel("-")
        self.num.setObjectName("statNum")
        self.num.setAlignment(Qt.AlignmentFlag.AlignCenter)
        cap = QLabel(caption)
        cap.setObjectName("statLbl")
        cap.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lay.addWidget(self.num)
        lay.addWidget(cap)

    def set(self, text):
        self.num.setText(text)


class AskPage(QWidget):
    status_changed = pyqtSignal(str)
    speed_changed = pyqtSignal(str)
    open_library = pyqtSignal()

    def __init__(self, get_engine, get_cfg):
        super().__init__()
        self.setObjectName("page")
        self.get_engine, self.get_cfg = get_engine, get_cfg
        self.history = []
        self.worker = None
        self.current = None

        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 16, 0, 16)
        lay.setSpacing(10)

        top = QHBoxLayout()
        top.setContentsMargins(24, 0, 24, 0)
        top.addWidget(header("Ask a question", "Answers come only from your indexed policies."))
        top.addStretch()
        self.new_btn = QPushButton("New chat")
        self.new_btn.clicked.connect(self.new_chat)
        top.addWidget(self.new_btn, alignment=Qt.AlignmentFlag.AlignTop)
        lay.addLayout(top)

        self.chat = ChatView()
        self.welcome = WelcomeView()
        self.welcome.open_library.connect(self.open_library)
        self.stack = QStackedWidget()
        self.stack.addWidget(self.welcome)
        self.stack.addWidget(self.chat)
        lay.addWidget(self.stack, 1)

        bar = QHBoxLayout()
        bar.setContentsMargins(24, 0, 24, 0)
        self.input = QLineEdit()
        self.input.setPlaceholderText("Ask about a policy...")
        self.input.returnPressed.connect(self._submit)
        bar.addWidget(self.input, 1)
        self.send = QPushButton("Send")
        self.send.setObjectName("primary")
        self.send.setMinimumWidth(90)
        self.send.clicked.connect(self._send_or_stop)
        bar.addWidget(self.send)
        lay.addLayout(bar)

    def set_stats(self, rows):
        self.welcome.set_stats(rows)

    def new_chat(self):
        if self.worker and self.worker.isRunning():
            self.worker.cancel()
            self.worker.wait()
        self.history.clear()
        self.chat.clear()
        self.stack.setCurrentWidget(self.welcome)
        self.input.setFocus()
        self.status_changed.emit("Ready")

    def _busy(self):
        return self.worker is not None and self.worker.isRunning()

    def _submit(self):
        if not self._busy():
            self.ask(self.input.text())

    def _send_or_stop(self):
        if self._busy():
            self.worker.cancel()
            self.send.setEnabled(False)
        else:
            self.ask(self.input.text())

    def ask(self, question):
        question = question.strip()
        if not question or self._busy():
            return
        self.input.clear()
        self.stack.setCurrentWidget(self.chat)
        self.chat.add(Bubble("user", question), align_right=True)
        self.current = self.chat.add(Bubble("ai", ""))
        self.send.setText("Stop")
        self.send.setObjectName("danger")
        self.send.setStyleSheet("")
        self.send.style().unpolish(self.send)
        self.send.style().polish(self.send)

        keep = self.get_cfg().history_turns * 2
        self.worker = AnswerWorker(self.get_engine(), question, list(self.history[-keep:]), self)
        w, bubble = self.worker, self.current
        w.status.connect(self.status_changed)
        w.sources.connect(lambda hits, b=bubble: self._show_sources(b, hits))
        self._buf = []
        w.token.connect(lambda t, b=bubble: self._on_token(b, t))
        w.finished_ok.connect(lambda text, secs, n, q=question, b=bubble: self._done(q, b, text, secs, n))
        w.failed.connect(lambda msg, b=bubble: self._failed(b, msg))
        w.start()

    def _on_token(self, bubble, tok):
        self._buf.append(tok)
        bubble.set_text("".join(self._buf))

    def _show_sources(self, bubble, hits):
        if hits:
            bubble.extra.addWidget(SourcesSection(hits))
        else:
            note = QLabel("No matching policy text was found.")
            note.setObjectName("muted")
            bubble.extra.addWidget(note)

    def _reset_send(self):
        self.send.setText("Send")
        self.send.setObjectName("primary")
        self.send.setEnabled(True)
        self.send.style().unpolish(self.send)
        self.send.style().polish(self.send)
        self.input.setFocus()

    def _done(self, question, bubble, text, secs, n):
        self._reset_send()
        self.status_changed.emit("Ready")
        if text.strip():
            self.history += [{"role": "user", "content": question},
                             {"role": "assistant", "content": text}]
            if secs > 0 and n:
                self.speed_changed.emit(f"{n / secs:.1f} tokens/s")
        elif not self._buf:
            bubble.set_text("Stopped.")

    def _failed(self, bubble, msg):
        self._reset_send()
        self.status_changed.emit("Error")
        err = Bubble("error", "Something went wrong.\n" + msg +
                     "\n\nCheck that Ollama is running and the database path in Settings is correct.")
        bubble.deleteLater()
        self.chat.add(err)


class SearchPage(QWidget):

    def __init__(self, get_engine):
        super().__init__()
        self.setObjectName("page")
        self.get_engine = get_engine
        self.worker = None
        lay = QVBoxLayout(self)
        lay.setContentsMargins(24, 16, 24, 16)
        lay.setSpacing(10)
        lay.addWidget(header("Policy search", "Find the exact policy text without generating an answer."))
        row = QHBoxLayout()
        self.input = QLineEdit()
        self.input.setPlaceholderText("Search policies...")
        self.input.returnPressed.connect(self.run)
        row.addWidget(self.input, 1)
        self.filter = QComboBox()
        self.filter.addItem("All policies", None)
        self.filter.setMinimumWidth(200)
        row.addWidget(self.filter)
        go = QPushButton("Search")
        go.setObjectName("primary")
        go.clicked.connect(self.run)
        row.addWidget(go)
        lay.addLayout(row)
        self.info = QLabel("")
        self.info.setObjectName("muted")
        lay.addWidget(self.info)
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        host = QWidget()
        host.setObjectName("chatHost")
        self.results = QVBoxLayout(host)
        self.results.setSpacing(8)
        self.results.addStretch()
        self.scroll.setWidget(host)
        lay.addWidget(self.scroll, 1)

    def set_documents(self, names):
        current = self.filter.currentData()
        self.filter.clear()
        self.filter.addItem("All policies", None)
        for n in names:
            self.filter.addItem(n, n)
        i = self.filter.findData(current)
        self.filter.setCurrentIndex(max(i, 0))

    def run(self):
        q = self.input.text().strip()
        if not q or (self.worker and self.worker.isRunning()):
            return
        self.info.setText("Searching...")
        eng = self.get_engine()
        self.worker = CallWorker(eng.search, q, eng.cfg.n_results, self.filter.currentData(), parent=self)
        self.worker.result.connect(self._show)
        self.worker.failed.connect(lambda m: self.info.setText("Search failed: " + m))
        self.worker.start()

    def _show(self, hits):
        while self.results.count() > 1:
            item = self.results.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        for i, h in enumerate(hits, 1):
            self.results.insertWidget(self.results.count() - 1, SourceCard(i, h, show_number=False))
        self.info.setText(f"{len(hits)} result{'s' if len(hits) != 1 else ''}" if hits else "No results.")


class DocCard(QFrame):
    reindex = pyqtSignal(str, str)
    remove = pyqtSignal(str, str)

    def __init__(self, name, source, context, count, date):
        super().__init__()
        self.setObjectName("card")
        c = theme.current()
        lay = QHBoxLayout(self)
        lay.setContentsMargins(16, 12, 12, 12)
        lay.setSpacing(12)

        info = QVBoxLayout()
        info.setSpacing(4)
        head = QHBoxLayout()
        head.setSpacing(8)
        title = QLabel(name)
        title.setStyleSheet("font-weight: 700; font-size: 15px;")
        head.addWidget(title)
        for text in (context or "uncategorized", f"{count} chunks") + ((f"added {date}",) if date else ()):
            b = QLabel(text)
            b.setObjectName("badge")
            head.addWidget(b)
        head.addStretch()
        info.addLayout(head)
        src = QLabel(source or "No source recorded")
        src.setObjectName("muted")
        src.setWordWrap(True)
        src.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        info.addWidget(src)
        lay.addLayout(info, 1)

        if source.lower().startswith("http"):
            open_btn = QPushButton("Open")
            open_btn.setToolTip("Open the original policy in your browser")
            open_btn.clicked.connect(lambda: QDesktopServices.openUrl(QUrl(source)))
            lay.addWidget(open_btn, alignment=Qt.AlignmentFlag.AlignVCenter)
        re_btn = QPushButton("Re-index")
        re_btn.setIcon(icons.button_icon("refresh", c["TEXT"]))
        re_btn.setToolTip("Rebuild this policy's searchable chunks from the saved original file")
        re_btn.clicked.connect(lambda: self.reindex.emit(name, context))
        lay.addWidget(re_btn, alignment=Qt.AlignmentFlag.AlignVCenter)
        rm_btn = QPushButton("Remove")
        rm_btn.setObjectName("danger")
        rm_btn.setIcon(icons.button_icon("trash", c["ERR"]))
        rm_btn.clicked.connect(lambda: self.remove.emit(name, context))
        lay.addWidget(rm_btn, alignment=Qt.AlignmentFlag.AlignVCenter)


class LibraryPage(QWidget):
    documents_loaded = pyqtSignal(list)
    rows_loaded = pyqtSignal(list)

    def __init__(self, get_engine):
        super().__init__()
        self.setObjectName("page")
        self.get_engine = get_engine
        self.worker = None
        lay = QVBoxLayout(self)
        lay.setContentsMargins(24, 16, 24, 16)
        lay.setSpacing(12)

        top = QHBoxLayout()
        top.addWidget(header("Library", "Policies currently indexed in the database."))
        top.addStretch()
        self.refresh_btn = QPushButton("Refresh")
        self.refresh_btn.setIcon(icons.button_icon("refresh", theme.current()["TEXT"]))
        self.refresh_btn.clicked.connect(self.refresh)
        top.addWidget(self.refresh_btn, alignment=Qt.AlignmentFlag.AlignTop)
        self.add_btn = QPushButton("Add document")
        self.add_btn.setObjectName("primary")
        self.add_btn.setIcon(icons.button_icon("plus", "#ffffff"))
        self.add_btn.clicked.connect(self.add_document)
        top.addWidget(self.add_btn, alignment=Qt.AlignmentFlag.AlignTop)
        lay.addLayout(top)

        stats = QHBoxLayout()
        stats.setSpacing(12)
        self.s_docs, self.s_chunks, self.s_last = StatTile("Policies"), StatTile("Chunks"), StatTile("Last added")
        for s in (self.s_docs, self.s_chunks, self.s_last):
            stats.addWidget(s)
        stats.addStretch()
        lay.addLayout(stats)

        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        host = QWidget()
        host.setObjectName("chatHost")
        self.cards = QVBoxLayout(host)
        self.cards.setContentsMargins(0, 0, 4, 0)
        self.cards.setSpacing(8)
        self.cards.addStretch()
        self.scroll.setWidget(host)
        lay.addWidget(self.scroll, 1)

        self.empty = QFrame()
        self.empty.setObjectName("emptyBox")
        el = QVBoxLayout(self.empty)
        el.setContentsMargins(30, 40, 30, 40)
        el.setSpacing(8)
        t = QLabel("No documents yet")
        t.setObjectName("h1")
        t.setAlignment(Qt.AlignmentFlag.AlignCenter)
        s = QLabel("Add a policy as a PDF, Word or text file and it becomes searchable right away.")
        s.setObjectName("muted")
        s.setAlignment(Qt.AlignmentFlag.AlignCenter)
        eb = QPushButton("Add your first document")
        eb.setObjectName("primary")
        eb.clicked.connect(self.add_document)
        el.addWidget(t)
        el.addWidget(s)
        el.addWidget(eb, alignment=Qt.AlignmentFlag.AlignCenter)
        self.empty.setVisible(False)
        lay.addWidget(self.empty)

        self.info = QLabel("")
        self.info.setObjectName("muted")
        lay.addWidget(self.info)

    def _buttons(self):
        return (self.add_btn, self.refresh_btn)

    def add_document(self):
        dlg = AddDocumentDialog(self.get_engine().cfg, self)
        dlg.exec()
        if dlg.added:
            self.refresh()

    def _run(self, job, done_msg):
        self.info.setText("Working...")
        for b in self._buttons():
            b.setEnabled(False)
        self.worker = IngestWorker(job, self)
        self.worker.progress.connect(lambda m, p: self.info.setText(m))

        def finish(_n=0):
            for b in self._buttons():
                b.setEnabled(True)
            self.refresh()
            self.info.setText(done_msg)

        def fail(msg):
            for b in self._buttons():
                b.setEnabled(True)
            self.info.setText("Failed: " + msg)
        self.worker.done.connect(finish)
        self.worker.failed.connect(fail)
        self.worker.start()

    def reindex(self, name, ctx):
        if self.worker and self.worker.isRunning():
            return
        cfg = self.get_engine().cfg
        self._run(run_job(cfg, lambda p: ingest.reindex_document(cfg, name, ctx, p)),
                  f"Re-indexed {name}.")

    def remove(self, name, ctx):
        if self.worker and self.worker.isRunning():
            return
        box = QMessageBox(self)
        box.setWindowTitle("Remove document")
        box.setText(f"Remove '{name}' from the library?")
        box.setInformativeText("It will no longer be searchable or used in answers. "
                               "The original file stays on disk.")
        box.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.Cancel)
        box.setDefaultButton(QMessageBox.StandardButton.Cancel)
        if box.exec() != QMessageBox.StandardButton.Yes:
            return
        cfg = self.get_engine().cfg

        def job(progress):
            ingest.remove_document(cfg, name, ctx)
            return 0
        self._run(run_job(cfg, job) if cfg.demo else job, f"Removed {name}.")

    def refresh(self):
        if self.worker and self.worker.isRunning():
            return
        self.info.setText("Loading...")
        self.worker = CallWorker(self.get_engine().library, parent=self)
        self.worker.result.connect(self._fill)
        self.worker.failed.connect(self._load_failed)
        self.worker.start()

    def _load_failed(self, msg):
        self.info.setText("Could not read the database: " + msg)
        self.rows_loaded.emit([])

    def _fill(self, rows):
        while self.cards.count() > 1:
            item = self.cards.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        for name, src, ctx, count, date in rows:
            card = DocCard(name, src, ctx, count, date)
            card.reindex.connect(self.reindex)
            card.remove.connect(self.remove)
            self.cards.insertWidget(self.cards.count() - 1, card)
        self.s_docs.set(str(len(rows)))
        self.s_chunks.set(f"{sum(r[3] for r in rows):,}")
        dates = [r[4] for r in rows if r[4]]
        self.s_last.set(max(dates) if dates else "-")
        self.scroll.setVisible(bool(rows))
        self.empty.setVisible(not rows)
        self.info.setText("")
        self.documents_loaded.emit([r[0] for r in rows])
        self.rows_loaded.emit(rows)


class SettingsPage(QWidget):
    saved = pyqtSignal()

    def __init__(self, cfg, get_engine):
        super().__init__()
        self.setObjectName("page")
        self.cfg, self.get_engine = cfg, get_engine
        self.worker = None
        lay = QVBoxLayout(self)
        lay.setContentsMargins(24, 16, 24, 16)
        lay.setSpacing(14)
        lay.addWidget(header("Settings"))
        form = QFormLayout()
        form.setSpacing(12)
        form.setLabelAlignment(Qt.AlignmentFlag.AlignLeft)

        self.model = QComboBox()
        self.model.setEditable(True)
        self.model.setMinimumWidth(280)
        self.model.setCurrentText(cfg.model)
        row = QHBoxLayout()
        row.addWidget(self.model, 1)
        reload_btn = QPushButton("Detect models")
        reload_btn.clicked.connect(self.detect_models)
        row.addWidget(reload_btn)
        form.addRow("Model", row)

        self.root = QLineEdit(cfg.root)
        form.addRow("Database folder", self.root)
        self.collection = QLineEdit(cfg.collection)
        form.addRow("Collection", self.collection)
        self.n = QSpinBox()
        self.n.setRange(1, 30)
        self.n.setValue(cfg.n_results)
        self.n.setMaximumWidth(120)
        form.addRow("Excerpts per question", self.n)
        self.turns = QSpinBox()
        self.turns.setRange(0, 12)
        self.turns.setValue(cfg.history_turns)
        self.turns.setMaximumWidth(120)
        form.addRow("Remembered turns", self.turns)
        self.theme = QComboBox()
        self.theme.addItem("Dark", "dark")
        self.theme.addItem("Light", "light")
        self.theme.setCurrentIndex(max(0, self.theme.findData(cfg.theme)))
        self.theme.setMaximumWidth(160)
        form.addRow("Appearance", self.theme)
        self.demo = QCheckBox("Demo mode (sample data, no Ollama or database needed)")
        self.demo.setChecked(cfg.demo)
        form.addRow("", self.demo)
        lay.addLayout(form)

        self.info = QLabel("")
        self.info.setObjectName("muted")
        lay.addWidget(self.info)
        btn = QPushButton("Save")
        btn.setObjectName("primary")
        btn.setMaximumWidth(120)
        btn.clicked.connect(self.save)
        lay.addWidget(btn)
        lay.addStretch()

    def detect_models(self):
        self.info.setText("Asking Ollama for installed models...")
        eng = self.get_engine()
        self.worker = CallWorker(eng.models, parent=self)
        self.worker.result.connect(self._models)
        self.worker.failed.connect(lambda m: self.info.setText("Could not reach Ollama: " + m))
        self.worker.start()

    def _models(self, names):
        cur = self.model.currentText()
        self.model.clear()
        self.model.addItems(names)
        self.model.setCurrentText(cur)
        self.info.setText(f"Found {len(names)} installed model(s).")

    def save(self):
        c = self.cfg
        c.model = self.model.currentText().strip() or c.model
        c.root = self.root.text().strip() or c.root
        c.collection = self.collection.text().strip() or c.collection
        c.n_results = self.n.value()
        c.history_turns = self.turns.value()
        c.demo = self.demo.isChecked()
        c.theme = self.theme.currentData()
        try:
            c.save()
            self.info.setText("Saved.")
        except OSError as e:
            self.info.setText(f"Could not save: {e}")
        self.saved.emit()
