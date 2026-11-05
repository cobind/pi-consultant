import json
import os
import time
from dataclasses import dataclass, asdict, field
from pathlib import Path

CONFIG_PATH = Path.home() / ".pocketlawyer.json"

SYSTEM_PROMPT = (
    "You are a policy assistant for a university professor. You are given numbered policy "
    "excerpts and a question. Answer in your own words in 2 to 6 short sentences, using only "
    "what the excerpts say. Include any conditions, limits or exceptions that apply (for example "
    "age requirements or prohibited items). Refer to excerpts like [1] when you rely on them. "
    "Never copy the excerpts word for word and never list them back. If the excerpts do not "
    "answer the question, say you could not find it in the policies."
)

NOT_FOUND = ("I could not find anything about that in the indexed policies. Try rephrasing the "
             "question, or add the relevant policy in the Library tab.")


@dataclass
class Config:
    root: str = os.environ.get("POCKET_LAWYER_ROOT", "/mnt/nvme0n1/database")
    collection: str = "Pocket_Lawyer"
    model: str = "qwen2.5:0.5b"
    n_results: int = 5
    max_distance: float = 1.5
    history_turns: int = 4
    demo: bool = False
    theme: str = "dark"

    @property
    def chroma_path(self):
        return str(Path(self.root) / "storage" / "chromadb")

    @classmethod
    def load(cls):
        cfg = cls()
        if CONFIG_PATH.exists():
            try:
                data = json.loads(CONFIG_PATH.read_text())
                for k, v in data.items():
                    if hasattr(cfg, k):
                        setattr(cfg, k, v)
            except (OSError, ValueError):
                pass
        return cfg

    def save(self):
        CONFIG_PATH.write_text(json.dumps(asdict(self), indent=2))


@dataclass
class Hit:
    text: str
    doc_name: str = "Unknown"
    doc_source: str = ""
    doc_context: str = ""
    index: int = 0
    distance: float = 0.0

    @property
    def relevance(self):
        return max(0, min(100, int(round(100 / (1 + self.distance)))))


def _hits_from_query(res):
    hits = []
    docs = res.get("documents", [[]])[0]
    metas = res.get("metadatas", [[]])[0]
    dists = (res.get("distances") or [[0] * len(docs)])[0]
    for text, meta, dist in zip(docs, metas, dists):
        meta = meta or {}
        hits.append(Hit(
            text=text,
            doc_name=meta.get("docName", "Unknown"),
            doc_source=meta.get("docSource", ""),
            doc_context=meta.get("docContext", ""),
            index=int(meta.get("index", 0)),
            distance=float(dist),
        ))
    return hits


def build_messages(question, hits, history, system=SYSTEM_PROMPT):
    """History holds only plain Q/A turns; excerpts are attached to the newest question
    only, so the context does not grow by 8 chunks every turn."""
    excerpts = "\n\n".join(
        f"[{i}] ({h.doc_name}) {h.text}" for i, h in enumerate(hits, 1)
    )
    msgs = [{"role": "system", "content": system}]
    msgs.extend(history)
    msgs.append({
        "role": "user",
        "content": f"Document excerpts:\n{excerpts}\n\nQuestion: {question}",
    })
    return msgs


class Engine:
    def __init__(self, cfg: Config):
        self.cfg = cfg
        self._collection = None

    def _col(self):
        if self._collection is None:
            import chromadb
            client = chromadb.PersistentClient(path=self.cfg.chroma_path)
            self._collection = client.get_collection(name=self.cfg.collection)
        return self._collection

    def search(self, query, n=None, doc_name=None):
        kwargs = {"query_texts": [query], "n_results": n or self.cfg.n_results}
        if doc_name:
            kwargs["where"] = {"docName": doc_name}
        return _hits_from_query(self._col().query(**kwargs))

    def retrieve(self, question, history=()):
        query = question
        if history and len(question.split()) <= 10:
            prev = next((m["content"] for m in reversed(history) if m["role"] == "user"), "")
            query = f"{prev} {question}".strip()
        hits = self.search(query)
        return [h for h in hits if h.distance <= self.cfg.max_distance]

    def library(self):
        data = self._col().get(include=["metadatas"])
        docs = {}
        for m in data["metadatas"]:
            key = (m.get("docName", "Unknown"), m.get("docContext", ""))
            entry = docs.setdefault(key, [key[0], m.get("docSource", ""), key[1], 0, ""])
            entry[3] += 1
        dates = self._dates()
        for e in docs.values():
            e[4] = dates.get((e[0], e[2]), "")
        return sorted((tuple(v) for v in docs.values()), key=lambda r: r[0].lower())

    def _dates(self):
        import sqlite3
        path = Path(self.cfg.root) / "storage" / "storage.db"
        try:
            con = sqlite3.connect(path)
            try:
                rows = con.execute("SELECT name, context, dateAdded FROM documents").fetchall()
            finally:
                con.close()
            return {(n, c): (d or "")[:10] for n, c, d in rows}
        except sqlite3.Error:
            return {}

    def models(self):
        import ollama
        resp = ollama.list()
        items = resp["models"] if isinstance(resp, dict) else resp.models
        names = []
        for m in items:
            names.append(m["model"] if isinstance(m, dict) else m.model)
        return names

    def stream(self, question, hits, history):
        import ollama
        msgs = build_messages(question, hits, history)
        for chunk in ollama.chat(model=self.cfg.model, messages=msgs, stream=True):
            yield chunk["message"]["content"]


class DemoEngine(Engine):
    _DOCS = [
        ("artificial_intelligence", "https://www.slu.edu/policies/artificial-intelligence", "sluPolicy"),
        ("tailgating", "https://www.slu.edu/policies/tailgating", "sluPolicy"),
        ("mandatory_training", "https://www.slu.edu/policies/mandatory-training", "sluPolicy"),
        ("ada", "https://www.slu.edu/policies/ada", "sluPolicy"),
        ("cellPolicy", "https://www.slu.edu/policies/cell-phone", "sluPolicy"),
    ]
    _TEXT = [
        "Faculty and staff may use approved generative AI tools for university work, provided that "
        "confidential, FERPA-protected, or otherwise restricted data is not entered into public tools.",
        "Employees must not allow an unauthorized person to follow them through a controlled access "
        "door. Report any person who cannot present valid identification to Campus Safety.",
        "All employees must complete the assigned information security training within 30 days of "
        "hire and annually thereafter. Completion is tracked by Human Resources.",
    ]

    def _col(self):
        raise RuntimeError("demo")

    def search(self, query, n=None, doc_name=None):
        time.sleep(0.4)
        out = []
        for i in range(min(n or 4, 4)):
            name, src, ctx = self._DOCS[i % len(self._DOCS)]
            if doc_name and name != doc_name:
                continue
            out.append(Hit(self._TEXT[i % 3], name, src, ctx, i, 0.35 + 0.2 * i))
        return out

    def library(self):
        return [(n, s, c, 6 + 3 * i, f"2026-10-{10 + i:02d}") for i, (n, s, c) in enumerate(self._DOCS)]

    def models(self):
        return ["qwen2.5:0.5b", "llama3.2", "gemma4:e4b"]

    def stream(self, question, hits, history):
        text = ("Based on the excerpts, **generative AI tools are permitted for university work**, "
                "but restricted data (for example FERPA-protected student records) must not be "
                "entered into public tools [1]. Training on this is mandatory and must be completed "
                "within 30 days of hire [3].\n\nIf you need to use a tool that is not on the approved "
                "list, ask your security office first.")
        for word in text.split(" "):
            time.sleep(0.03)
            yield word + " "


def make_engine(cfg: Config):
    return DemoEngine(cfg) if cfg.demo else Engine(cfg)
