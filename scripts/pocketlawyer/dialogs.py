import time
from pathlib import Path

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (QComboBox, QDialog, QFileDialog, QFormLayout, QHBoxLayout, QLabel,
                             QLineEdit, QPlainTextEdit, QProgressBar, QPushButton, QVBoxLayout)

from . import ingest
from .workers import CallWorker, IngestWorker


def run_job(cfg, real_fn):
    if not cfg.demo:
        return real_fn

    def fake(progress):
        for msg, pct in [("Getting the file...", 10), ("Reading the text...", 35),
                         ("Splitting into chunks...", 55), ("Indexing...", 80)]:
            progress(msg, pct)
            time.sleep(0.4)
        progress("Done. Indexed 24 chunks. (demo - nothing was saved)", 100)
        return 24
    return fake


class AddDocumentDialog(QDialog):
    def __init__(self, cfg, parent=None):
        super().__init__(parent)
        self.cfg = cfg
        self.setWindowTitle("Add document")
        self.setMinimumWidth(620)
        self.added = False
        self.worker = None
        self.setAcceptDrops(True)

        lay = QVBoxLayout(self)
        lay.setContentsMargins(20, 18, 20, 18)
        lay.setSpacing(12)
        title = QLabel("Add a document")
        title.setObjectName("h1")
        lay.addWidget(title)
        hint = QLabel("Choose a file (PDF, Word or text), drop one here, or paste a link to a PDF.")
        hint.setObjectName("muted")
        lay.addWidget(hint)

        form = QFormLayout()
        form.setSpacing(10)
        row = QHBoxLayout()
        self.file = QLineEdit()
        self.file.setPlaceholderText("C:\\path\\to\\policy.pdf  or  https://...")
        self.file.editingFinished.connect(self._autofill)
        row.addWidget(self.file, 1)
        browse = QPushButton("Browse...")
        browse.clicked.connect(self._browse)
        row.addWidget(browse)
        form.addRow("File or link", row)
        self.name = QLineEdit()
        self.name.setPlaceholderText("e.g. Tailgating Policy")
        form.addRow("Name", self.name)
        self.source = QLineEdit()
        self.source.setPlaceholderText("Link to the policy page, or a short description")
        form.addRow("Source", self.source)
        self.context = QComboBox()
        self.context.setEditable(True)
        try:
            self.context.addItems(["sluPolicy"] if cfg.demo else ingest.list_contexts(cfg))
        except OSError:
            self.context.addItem("sluPolicy")
        form.addRow("Category", self.context)
        lay.addLayout(form)

        self.preview_btn = QPushButton("Preview extracted text")
        self.preview_btn.clicked.connect(self._preview)
        lay.addWidget(self.preview_btn, alignment=Qt.AlignmentFlag.AlignLeft)
        self.preview = QPlainTextEdit()
        self.preview.setReadOnly(True)
        self.preview.setMinimumHeight(150)
        self.preview.setVisible(False)
        lay.addWidget(self.preview)

        self.bar = QProgressBar()
        self.bar.setVisible(False)
        self.bar.setTextVisible(False)
        self.bar.setFixedHeight(8)
        lay.addWidget(self.bar)
        self.info = QLabel("")
        self.info.setWordWrap(True)
        self.info.setObjectName("muted")
        lay.addWidget(self.info)

        btns = QHBoxLayout()
        btns.addStretch()
        self.cancel = QPushButton("Close")
        self.cancel.clicked.connect(self.reject)
        btns.addWidget(self.cancel)
        self.go = QPushButton("Add to library")
        self.go.setObjectName("primary")
        self.go.clicked.connect(self._add)
        btns.addWidget(self.go)
        lay.addLayout(btns)

    def dragEnterEvent(self, e):
        if e.mimeData().hasUrls():
            e.acceptProposedAction()

    def dropEvent(self, e):
        urls = e.mimeData().urls()
        if urls:
            self.file.setText(urls[0].toLocalFile() or urls[0].toString())
            self._autofill()

    def _browse(self):
        path, _ = QFileDialog.getOpenFileName(self, "Choose a document", "",
                                              "Documents (*.pdf *.docx *.txt *.md);;All files (*)")
        if path:
            self.file.setText(path)
            self._autofill()

    def _autofill(self):
        if self.name.text().strip():
            return
        text = self.file.text().strip()
        if text and not text.lower().startswith("http"):
            self.name.setText(Path(text).stem.replace("_", " ").replace("-", " ").title())

    def _set_busy(self, busy):
        for w in (self.go, self.preview_btn, self.file, self.name, self.source, self.context):
            w.setEnabled(not busy)
        self.bar.setVisible(busy or self.bar.value() > 0)

    def _preview(self):
        path = self.file.text().strip()
        if not path or path.lower().startswith("http"):
            self.info.setText("Preview works on a file on this computer. Choose a file first.")
            return
        self.info.setText("Reading...")
        self.worker = CallWorker(ingest.preview, path, parent=self)
        self.worker.result.connect(self._show_preview)
        self.worker.failed.connect(lambda m: self.info.setText(m.split(": ", 1)[-1]))
        self.worker.start()

    def _show_preview(self, res):
        text, n = res
        self.preview.setPlainText(text[:3000] + ("\n..." if len(text) > 3000 else ""))
        self.preview.setVisible(True)
        self.info.setText(f"{len(text):,} characters, will become {n} chunks.")

    def _add(self):
        src, name, source = self.file.text().strip(), self.name.text().strip(), self.source.text().strip()
        ctx = self.context.currentText().strip() or "sluPolicy"
        if not src:
            self.info.setText("Choose a file or paste a link first.")
            return
        if src.lower().startswith("http") and not source:
            source = src
            self.source.setText(src)
        job = run_job(self.cfg, lambda progress: ingest.add_document(self.cfg, src, name, source, ctx, progress))
        self.bar.setValue(0)
        self.bar.setVisible(True)
        self._set_busy(True)
        self.worker = IngestWorker(job, self)
        self.worker.progress.connect(lambda m, p: (self.info.setText(m), self.bar.setValue(p)))
        self.worker.done.connect(self._done)
        self.worker.failed.connect(self._failed)
        self.worker.start()

    def _done(self, n):
        self.added = True
        self._set_busy(False)
        self.go.setText("Add another")
        self.cancel.setText("Done")
        self.info.setText(f"Added. {n} chunks are now searchable.")
        for w in (self.file, self.name, self.source):
            w.clear()

    def _failed(self, msg):
        self._set_busy(False)
        self.bar.setVisible(False)
        self.info.setText("Could not add this document: " + msg)
