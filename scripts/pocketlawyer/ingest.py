import re
import shutil
import sqlite3
import urllib.request
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse, unquote

CHUNK_SIZE = 500
CHUNK_OVERLAP = 50
SUPPORTED = (".pdf", ".txt", ".md", ".docx")

SCHEMA = """CREATE TABLE IF NOT EXISTS documents(
    id INTEGER PRIMARY KEY, name TEXT NOT NULL, fileNameStem TEXT NOT NULL,
    context TEXT NOT NULL, source TEXT NOT NULL, dateAdded TEXT, UNIQUE(name, context))"""

class IngestError(Exception):
    pass


def _noop(msg, pct):
    pass


def storage_dir(cfg):
    return Path(cfg.root) / "storage"


def db_path(cfg):
    return storage_dir(cfg) / "storage.db"


def slug(text):
    s = re.sub(r"[^A-Za-z0-9_-]+", "_", text.strip()).strip("_")
    return s or "document"


def list_contexts(cfg):
    base = storage_dir(cfg)
    found = {p.name for p in base.glob("*") if (p / "rawDocuments").is_dir()} if base.is_dir() else set()
    return sorted(found) or ["sluPolicy"]


def extract_text(path):
    path = Path(path)
    ext = path.suffix.lower()
    if ext == ".pdf":
        from pypdf import PdfReader
        try:
            pages = [(p.extract_text() or "") for p in PdfReader(str(path)).pages]
        except Exception as e:
            raise IngestError(f"Could not read this PDF ({e}).")
        text = "\n\n".join(pages)
        if not text.strip():
            raise IngestError("This PDF has no selectable text (it may be a scan). "
                              "It would need OCR before it can be indexed.")
        return text
    if ext in (".txt", ".md"):
        return path.read_text(encoding="utf-8", errors="replace")
    if ext == ".docx":
        try:
            import docx
        except ImportError:
            raise IngestError("Word files need the python-docx package: pip install python-docx")
        return "\n\n".join(p.text for p in docx.Document(str(path)).paragraphs)
    raise IngestError(f"Unsupported file type {ext or '(none)'}. Supported: {', '.join(SUPPORTED)}")


def _is_heading(line):
    return (0 < len(line) <= 70 and line[0].isupper() and not line.endswith((".", ",", ";"))
            and not line.startswith("•"))


def clean_text(text):
    """Same cleanup as sanitizeDocument.py, but structure is kept.

    The original joined lines with the literal characters '/n' and treated whitespace-only
    lines as text, so every policy became one long line. Here, blank lines, headings and
    bullets stay as paragraph breaks so the chunker can split on them.
    """
    t = text.encode("utf-8", "ignore").decode("utf-8")
    t = t.replace("\r\n", "\n").replace("\r", "\n")
    t = re.sub(r"\d[\W]+[P][\s]+[a][\s]+[g][\s]+[e]", "", t)      # SLU "Page" artifact
    t = "\n".join(line.strip() for line in t.split("\n"))
    t = re.sub(r"(\w+)-\n(\w+)", r"\1\2", t)
    lines = t.split("\n")
    out = []
    for i, line in enumerate(lines):
        prev = lines[i - 1] if i > 0 else ""
        nxt = lines[i + 1] if i + 1 < len(lines) else ""
        heading = _is_heading(line) and nxt and (not prev or prev.endswith((".", ":", ";", "!", "?")))
        if line.startswith("•") or heading:
            out.append("")
        out.append(line)
        if heading:
            out.append("")
    t = "\n".join(out)
    t = re.sub(r"[ \t]+", " ", t)
    t = re.sub(r"(?<!\n)\n(?!\n)", " ", t)
    t = re.sub(r"\n{3,}", "\n\n", t)
    return t.strip()


def split_chunks(text):
    try:
        from langchain_text_splitters import RecursiveCharacterTextSplitter
        splitter = RecursiveCharacterTextSplitter(
            chunk_size=CHUNK_SIZE, chunk_overlap=CHUNK_OVERLAP,
            separators=["\n\n", "\n", ". ", " "])
        return splitter.split_text(text)
    except ImportError:
        return _simple_split(text)


def _simple_split(text):
    pieces = []
    for para in text.split("\n\n"):
        if len(para) <= CHUNK_SIZE:
            pieces.append(para)
        else:
            pieces += re.split(r"(?<=[.!?])\s+", para)
    chunks, cur = [], ""
    for p in pieces:
        if cur and len(cur) + len(p) + 1 > CHUNK_SIZE:
            chunks.append(cur)
            cur = cur[-CHUNK_OVERLAP:] + " " + p
        else:
            cur = (cur + "\n" + p) if cur else p
    if cur.strip():
        chunks.append(cur)
    return [c.strip() for c in chunks if c.strip()]


def preview(path):
    cleaned = clean_text(extract_text(path))
    return cleaned, len(split_chunks(cleaned))


def download(url, dest_dir):
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https"):
        raise IngestError("Only http(s) links can be downloaded.")
    name = unquote(Path(parsed.path).name) or "download"
    req = urllib.request.Request(url, headers={"User-Agent": "PocketLawyer/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            ctype = resp.headers.get("Content-Type", "")
            data = resp.read()
    except Exception as e:
        raise IngestError(f"Download failed: {e}")
    if not Path(name).suffix:
        name += ".pdf" if "pdf" in ctype or data[:4] == b"%PDF" else ".html"
    if Path(name).suffix.lower() not in SUPPORTED:
        raise IngestError("That link is not a PDF or text document. Download the PDF and add the file instead.")
    dest = Path(dest_dir) / name
    dest.write_bytes(data)
    return dest


def _collection(cfg):
    import chromadb
    client = chromadb.PersistentClient(path=cfg.chroma_path)
    return client.get_or_create_collection(name=cfg.collection)


def _db(cfg):
    storage_dir(cfg).mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(db_path(cfg))
    con.execute(SCHEMA)
    return con


def _find_row(con, name, context):
    return con.execute("SELECT id, name, fileNameStem, context, source FROM documents "
                       "WHERE name = ? AND context = ?", (name, context)).fetchone()


# ---------------------------------------------------------------- public API
def add_document(cfg, file_or_url, name, source, context, progress=_noop):
    """Copy, extract, clean, chunk and index one document. Re-adding the same
    (name, context) replaces the old version instead of failing. Returns chunk count."""

    name, source, context = name.strip(), source.strip(), slug(context)
    if not name:
        raise IngestError("Give the document a name.")
    if not source:
        raise IngestError("Give the document a source (a link or a short description).")

    ctx_dir = storage_dir(cfg) / context
    raw_dir, ready_dir = ctx_dir / "rawDocuments", ctx_dir / "readReady"
    raw_dir.mkdir(parents=True, exist_ok=True)
    ready_dir.mkdir(parents=True, exist_ok=True)

    progress("Getting the file...", 5)
    src = str(file_or_url).strip()
    if src.lower().startswith(("http://", "https://")):
        src_path = download(src, raw_dir)
    else:
        src_path = Path(src).expanduser()
        if not src_path.is_file():
            raise IngestError(f"File not found: {src_path}")
    stem = slug(src_path.stem)
    raw_path = raw_dir / (stem + src_path.suffix.lower())
    if src_path.resolve() != raw_path.resolve():
        shutil.copy(src_path, raw_path)

    progress("Reading the text...", 20)
    cleaned = clean_text(extract_text(raw_path))
    if len(cleaned) < 40:
        raise IngestError("Almost no text was found in this file.")
    (ready_dir / (stem + ".txt")).write_text(cleaned, encoding="utf-8")

    progress("Splitting into chunks...", 40)
    chunks = split_chunks(cleaned)

    progress("Saving to the database...", 55)
    con = _db(cfg)
    try:
        con.execute("INSERT INTO documents (name, fileNameStem, context, source, dateAdded) "
                    "VALUES (?,?,?,?,?) ON CONFLICT(name, context) DO UPDATE SET "
                    "fileNameStem=excluded.fileNameStem, source=excluded.source, dateAdded=excluded.dateAdded",
                    (name, stem, context, source, str(datetime.now())))
        con.commit()
    finally:
        con.close()

    progress("Indexing (this can take a moment)...", 70)
    col = _collection(cfg)
    col.delete(where={"$and": [{"docName": name}, {"docContext": context}]})
    col.add(
        ids=[f"{context}_{stem}_{i}" for i in range(len(chunks))],
        documents=chunks,
        metadatas=[{"originFile": str(ready_dir / (stem + ".txt")), "index": i, "docName": name,
                    "docContext": context, "docSource": source} for i in range(len(chunks))],
    )
    progress(f"Done. Indexed {len(chunks)} chunks.", 100)
    return len(chunks)


def reindex_document(cfg, name, context, progress=_noop):
    con = _db(cfg)
    try:
        row = _find_row(con, name, context)
    finally:
        con.close()
    if not row:
        raise IngestError("That document is not in the database.")
    raw_dir = storage_dir(cfg) / context / "rawDocuments"
    matches = sorted(raw_dir.glob(row[2] + ".*"))
    if not matches:
        raise IngestError(f"The original file for '{name}' is missing from {raw_dir}.")
    return add_document(cfg, matches[0], name, row[4], context, progress)


def remove_document(cfg, name, context, delete_files=False):
    col = _collection(cfg)
    col.delete(where={"$and": [{"docName": name}, {"docContext": context}]})
    con = _db(cfg)
    try:
        row = _find_row(con, name, context)
        con.execute("DELETE FROM documents WHERE name = ? AND context = ?", (name, context))
        con.commit()
    finally:
        con.close()
    if delete_files and row:
        stem = row[2]
        base = storage_dir(cfg) / context
        for f in list((base / "rawDocuments").glob(stem + ".*")) + [base / "readReady" / (stem + ".txt")]:
            f.unlink(missing_ok=True)
