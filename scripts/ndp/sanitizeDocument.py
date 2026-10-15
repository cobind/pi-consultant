# Christian Caillouet - 9/30/2026

import sys
import re

from pathlib import Path
from pypdf import PdfReader

# -------------------------------
#       FUNCTIONS
# -------------------------------
def processPdf(source, destination):
    reader = PdfReader(source)
    textArray = []

    for page in reader.pages:
        text = page.extract_text()
        if text:
            textArray.append(text)

    fullText = "\n".join(textArray)


    cleaned = fullText.encode("utf-8", "ignore").decode("utf-8")

    # Removing weird artifact SLU policy docs leave behind
    cleaned = re.sub(r'\d[\W]+[P][\s]+[a][\s]+[g][\s]+[e]', '', cleaned)

    # I am NOT going to lie this a bunch of AI-generated regex so I have no clue what its really doing
    #   I HATE AI GENERATED CODE THIS IS A COMPROMISE OF MY MORALS
    #   BUT FUCK REGEX ISNT EVEN THE POINT OF THE PROJECT
    cleaned = re.sub(r'(\w+)-\s*\n\s*(\w+)', r'\1\2', cleaned)
    cleaned = re.sub(r'(?<!\n)\n(?!\n)', ' ', cleaned)
    cleaned = re.sub(r'[ \t]+', ' ', cleaned)
    cleaned = "/n".join([line.strip() for line in cleaned.splitlines()])
    cleaned = re.sub(r'\n{3,}', '\n\n', cleaned)

    with open(destination, "w", encoding="utf-8") as textFile:
        textFile.write(cleaned)

# -------------------------------
#       SETUP
# -------------------------------
storageDirectoryStr = "/mnt/nvme0n1/database/storage/"

if len(sys.argv) < 2:
    print("Usage: python3 sanitizeDocument.py <documentFilePath>")
    sys.exit(1)

docPathStr = sys.argv[1]
# Check user-provided file path exists
docPath = Path(docPathStr)
if not docPath.is_file() or "rawDocuments" not in docPathStr:
    print("Error: " + docPathStr + " is not a valid file path.")
    sys.exit()

docName = docPath.stem

contextStoragePath = docPath.parent.parent

destinationPathStr = "".join([str(contextStoragePath), "/readReady/", docName, ".txt"])
destinationPath = Path(destinationPathStr)
print(" ---------- sanitizeDocument.py ----------") # mmm formatting yumy

# -------------------------------
#       TEXT FILE CREATION
# -------------------------------
fileExtension = str(docPath.suffix)

match fileExtension:
    case ".pdf":
        processPdf(docPath, destinationPath)
    case _:
        print("Error: No sanitization method implemented for " + fileExtension + " files.")
        sys.exit()

print("Output saved to " + destinationPathStr)
print(" - sanitizeDocument.py completed successfully! - ")
