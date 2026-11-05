import time
from PyQt6.QtCore import QThread, pyqtSignal


class AnswerWorker(QThread):
    status = pyqtSignal(str)
    sources = pyqtSignal(list)
    token = pyqtSignal(str)
    finished_ok = pyqtSignal(str, float, int)
    failed = pyqtSignal(str)

    def __init__(self, engine, question, history, parent=None):
        super().__init__(parent)
        self.engine, self.question, self.history = engine, question, history
        self._cancel = False

    def cancel(self):
        self._cancel = True

    def run(self):
        try:
            self.status.emit("Searching policies...")
            hits = self.engine.retrieve(self.question, self.history)
            self.sources.emit(hits)
            if self._cancel:
                return self.finished_ok.emit("", 0.0, 0)
            if not hits:
                from .backend import NOT_FOUND
                self.token.emit(NOT_FOUND)
                return self.finished_ok.emit("", 0.0, 0)
            self.status.emit("Thinking...")
            start, n, parts, first = time.time(), 0, [], None
            for tok in self.engine.stream(self.question, hits, self.history):
                if self._cancel:
                    break
                if first is None:
                    first = time.time()
                    self.status.emit("Answering...")
                n += 1
                parts.append(tok)
                self.token.emit(tok)
            gen_time = time.time() - (first or start)
            self.finished_ok.emit("".join(parts), gen_time, n)
        except Exception as e:
            self.failed.emit(f"{type(e).__name__}: {e}")


class CallWorker(QThread):
    result = pyqtSignal(object)
    failed = pyqtSignal(str)

    def __init__(self, fn, *args, parent=None):
        super().__init__(parent)
        self.fn, self.args = fn, args

    def run(self):
        try:
            self.result.emit(self.fn(*self.args))
        except Exception as e:
            self.failed.emit(f"{type(e).__name__}: {e}")


class IngestWorker(QThread):
    progress = pyqtSignal(str, int)
    done = pyqtSignal(int)
    failed = pyqtSignal(str)

    def __init__(self, fn, parent=None):
        super().__init__(parent)
        self.fn = fn

    def run(self):
        try:
            n = self.fn(lambda msg, pct: self.progress.emit(msg, pct))
            self.done.emit(n)
        except Exception as e:
            from .ingest import IngestError
            self.failed.emit(str(e) if isinstance(e, IngestError) else f"{type(e).__name__}: {e}")
