# Christian Caillouet - 10/1/2026

import sys
import subprocess

from pathlib import Path

# -------------------------------
#       SETUP
# -------------------------------
storageDirectoryStr = "/mnt/nvme0n1/database/storage/"

sqliteDbPathStr = storageDirectoryStr + "storage.db"

if len(sys.argv) < 3:
    print("Usage: python3 start.py <documentFilePath> <context>")
    sys.exit(1)

docEntryPathStr = sys.argv[1]
docContext = sys.argv[2]

docFileNameStem = str(Path(docEntryPathStr).stem)
docFileExtension = str(Path(docEntryPathStr).suffix)

rawDocPathStr = "".join([storageDirectoryStr, docContext, "/rawDocuments/", docFileNameStem, docFileExtension])
cleanDocPathStr = "".join([storageDirectoryStr, docContext, "/readReady/", docFileNameStem, ".txt"])


tasks = [
    ["python", "/mnt/nvme0n1/database/scripts/ndp/addDocument.py", docEntryPathStr, docContext],
    ["python", "/mnt/nvme0n1/database/scripts/ndp/sanitizeDocument.py", rawDocPathStr],
    ["python", "/mnt/nvme0n1/database/scripts/ndp/chunkDocument.py", cleanDocPathStr]
]

# -------------------------------
#       yeah idk man whatever
# -------------------------------
for task in tasks:
    print(f"Starting {' '.join(task)}")

    result = subprocess.call(task)
