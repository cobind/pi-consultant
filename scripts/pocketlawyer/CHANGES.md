# What changed (Pocket Lawyer GUI work)

Nothing that existed before was edited. Everything is new, in `scripts/pocketlawyer/`,
except one added line in `.gitignore`.

## Untouched (original code)
- `scripts/gui.py` (old window, still runs)
- `scripts/AskQwen.py`, `AskQwenStream.py`, `ClientTest.py`, `GoogleSearch.py`
- `scripts/ndp/*` (addDocument, sanitizeDocument, chunkDocument, start)
- `storage/` (policies, ChromaDB, storage.db)

## Edited (1 line)
- `.gitignore`: added `__pycache__/`

## New files, in the order I would read them
| File | Lines | What it is |
|---|---|---|
| `backend.py` | 216 | Settings, ChromaDB search, Ollama streaming, prompt, relevance cutoff, demo data |
| `workers.py` | 81 | Background threads (answering, adding documents) so the window never freezes |
| `ingest.py` | 289 | New add / re-index / remove pipeline (merged version of `ndp/*`, with fixes) |
| `app.py` | 115 | Main window, sidebar, status bar, startup options (`--demo`, `--root`) |
| `pages.py` | 443 | The four screens: Ask, Search, Library, Settings |
| `widgets.py` | 190 | Chat bubbles, source cards, scrolling chat view |
| `dialogs.py` | 182 | The Add document dialog |
| `theme.py` | 51 | Colors and styling |
| `pi/pocket-lawyer.sh` | 15 | Launcher for the Pi |
| `pi/PocketLawyer.desktop` | 8 | Pi desktop shortcut |
| `pi/pocket-lawyer.svg` / `.ico` | | Icon (Pi / Windows) |
| `README.md` | | How to run it |

## Where the important changes are
- Model, number of excerpts, relevance cutoff: `backend.py`, class `Config`
- System prompt for the model: `backend.py`, `SYSTEM_PROMPT`
- Follow-up questions keeping context: `backend.py`, `Engine.retrieve`
- Chunk size and overlap: `ingest.py`, `CHUNK_SIZE`, `CHUNK_OVERLAP`
- Text cleanup (the old `/n` bug fix): `ingest.py`, `clean_text`
- Colors: `theme.py`
- Sidebar and window size: `app.py`

## Bugs fixed compared with the old code
- `AskQwenStream.py`: role typo `'assisstant'`; excerpts piling up in history every turn;
  `modelFile` system prompt never used; `getChromaResults` read a global instead of its argument.
- `sanitizeDocument.py`: joins lines with the literal text `/n`, flattening every policy into one line.
- `addDocument.py`: builds SQL with `.format()` (breaks on apostrophes).
- `chunkDocument.py`: fixed chunk IDs, so adding a document again fails.
(The originals are left as they are; the new code does not depend on them.)

## Review with git
    git diff 38335eca --stat                        # all changes since before the GUI work
    git diff 38335eca -- scripts/pocketlawyer/pages.py
    git log --oneline                               # one commit per round of changes
Go back completely:  `git checkout 38335eca`   (or delete the `scripts/pocketlawyer` folder)


## v7 visual update

- New file: `scripts/pocketlawyer/icons.py` (sidebar, button and app icons drawn as SVG, no image files needed).
- `theme.py`: dark and light palettes. Choose under Settings > Appearance; saved as `theme` in `~/.pocketlawyer.json`.
- `pages.py`: welcome screen on Ask (logo, policy and chunk counts), card-style Library with stats, category/chunk/date badges, Open, Re-index and Remove per document.
- `widgets.py`: wider answer bubbles and an animated thinking indicator (no avatars).
- `backend.py`: Library rows now include the date added (read from `storage/storage.db`).
- `app.py`: sidebar icons, window icon, Windows taskbar icon id, theme switching.
