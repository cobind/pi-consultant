#!/bin/bash
# Starts Pocket Lawyer on the Orange Pi. Works from any folder, and from a desktop shortcut.
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"   # the folder that contains bin/ and scripts/
LOG="$HOME/pocketlawyer.log"

cd "$ROOT" || exit 1

# Start Ollama if it is not already running (the app needs it to write answers).
if command -v ollama >/dev/null 2>&1 && ! pgrep -x ollama >/dev/null 2>&1; then
    nohup ollama serve >>"$LOG" 2>&1 &
    sleep 3
fi

echo "--- $(date) starting Pocket Lawyer from $ROOT" >>"$LOG"
exec "$ROOT/bin/python" -m scripts.pocketlawyer.app --root "$ROOT" "$@" >>"$LOG" 2>&1
