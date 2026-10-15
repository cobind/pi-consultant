# Christian Caillouet - 9/30/2026

import sys
import sqlite3
import chromadb

from pathlib import Path
from chromadb.utils.embedding_functions import DefaultEmbeddingFunction
from langchain_text_splitters import RecursiveCharacterTextSplitter

# -------------------------------
#       SETUP
# -------------------------------
storageDirectoryStr = "/mnt/nvme0n1/database/storage/"

sqliteDbPathStr = storageDirectoryStr + "storage.db"

if len(sys.argv) < 2:
    print("Usage: python3 sanitizeDocument.py <documentFilePath>")
    sys.exit(1)

docPathStr = sys.argv[1]
# Check user-provided file path exists
docPath = Path(docPathStr)
if not docPath.is_file() or "readReady" not in docPathStr:
    print("Error: " + docPathStr + " is not a valid file path.")
    sys.exit()

docName = docPath.stem
context = str(docPath.parent.parent.stem)
#print(docName)
#print(context)

# AI nonsense or whatever
client = chromadb.PersistentClient(path='/mnt/nvme0n1/database/storage/chromadb')
collection = client.get_or_create_collection(name = "Pocket_Lawyer")

print(" ---------- chunkDocument.py ----------") # mmm formatting yumy

# -------------------------------
#   SQLITE QUERY
# -------------------------------
dbConnection = sqlite3.connect(sqliteDbPathStr)
dbCursor = dbConnection.cursor()

searchQuery = "SELECT * FROM documents WHERE fileNameStem LIKE '{}' AND context LIKE '{}'".format(docName, context)

dbCursor.execute(searchQuery)
docInfo = dbCursor.fetchone()

dbConnection.close()

# -------------------------------
#   CHUNKING WOOOOO
# -------------------------------

with open(docPathStr) as f:
    docuContents = f.read()

splitter = RecursiveCharacterTextSplitter(
        chunk_size=500,
        chunk_overlap=50,
        separators=["\n\n", "\n", ". ", " "]
)

chunks = splitter.split_text(docuContents)
print("Generated " + str(len(chunks)) + " chunks from " + docPathStr)

# Preparing data for collection
ids = []
documents = []
metadatas = []

print("Preparing chunk data...")
for i, chunk in enumerate(chunks):
    documents.append(chunk)
    ids.append("{}_{}_{}".format(context, docName, i))

    metadatas.append({
        "originFile": docPathStr,
        "index": i,
        #"docId": docInfo[0],
        "docName": docInfo[1],
        "docContext": context,
        "docSource": docInfo[4],
    })

print("Adding chunk data to collection...")
collection.add(ids=ids,documents=documents,metadatas=metadatas)

print("Finished!")
print(" - chunkDocument.py completed successfully! - ")
