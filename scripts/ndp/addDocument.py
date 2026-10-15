# Christian Caillouet - 9/30/2026

import sys
import sqlite3
import shutil

from pathlib import Path
from datetime import datetime
from pypdf import PdfReader

# -------------------------------
#       FUNCTIONS
# -------------------------------
def askYN(prompt):
    print(prompt)
    while True:
        answer = input("(y/n): ").strip().lower()
        if answer in ['y', 'yes']:
            return True
        if answer in ['n', 'no']:
            return False
        print("Invalid input :(")

# -------------------------------
#       SETUP
# -------------------------------
storageDirectoryStr = "/mnt/nvme0n1/database/storage/"

sqliteDbPathStr = storageDirectoryStr + "storage.db"

if len(sys.argv) < 3:
    print("Usage: python3 addDocument.py <documentFilePath> <context>")
    sys.exit(1)

docPathStr = sys.argv[1]
docContext = sys.argv[2]

# Check user-provided file path exists
docPath = Path(docPathStr)
if not docPath.is_file():
    print("Error: " + docPathStr + " is not a valid file path.")
    sys.exit()

docFileNameStem = docPath.stem

print(" ---------- addDocument.py ----------") # mmm formatting yumy

# -------------------------------
#       FILE MANAGEMENT
# -------------------------------

# Check if context has a directory in rawDocuments
contextSubdirectoryStr = "".join([storageDirectoryStr, docContext])
contextSubdirectory = Path(contextSubdirectoryStr)
rawDocsPath = Path("".join([contextSubdirectoryStr, "/rawDocuments"]))
readReadyPath = Path("".join([contextSubdirectoryStr, "/readReady"]))

if not contextSubdirectory.is_dir():
    if not askYN("Document context " + docContext + " has not been used previously. Proceed?"):
        sys.exit()
    else: # Create directories
        rawDocsPath.mkdir(parents=True, exist_ok=True)
        readReadyPath.mkdir(parents=True, exist_ok=True)

# Create a copy to stay in storage
shutil.copy(docPathStr, "".join([contextSubdirectoryStr, "/rawDocuments"]))

# -------------------------------
#       SQLITE NONSENSE
# -------------------------------

#   storage.db contents
#--------------------------------
#   TABLE documents
#           - id INTEGER PRIMARY KEY
#           - name TEXT NOT NULL
#           - fileNameStem TEXT NOT NULL
#           - context TEXT NOT NULL
#                   The context the document should be referenced in (SLU Policy, Federal/State Law, etc.)
#           - source TEXT NOT NULL
#                   A description (or link to) the document source
#           - dateAdded TEXT

dbConnection = sqlite3.connect(sqliteDbPathStr)
dbCursor = dbConnection.cursor()

# Harvest values!!
docName = input("Enter an appropiate name for this document: ")
docSource = input("Please provide an appropiate source: ")

# Create and execute query
insertQuery = "INSERT INTO documents (name, fileNameStem, context, source, dateAdded) VALUES('{}', '{}', '{}', '{}', '{}')".format(docName, docFileNameStem, docContext, docSource, datetime.now())
#print("Query: " + insertQuery)
dbCursor.execute(insertQuery)

# Save changes
dbConnection.commit()
dbConnection.close()
print(" - addDocument.py completed successfully! - ")
