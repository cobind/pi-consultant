import sys
import shutil
from pathlib import Path
from pypdf import PdfReader

# ----------------------------------------
#   Create file paths
# ----------------------------------------

# Run python file with name of file to extract as argument
fileName = sys.argv[1]
fileContext = sys.argv[2]

rawDocumentFilePathBase = "/mnt/nvme0n1/database/storage/rawDocuments/"
downloadFilePathBase = "/home/citrus/Downloads/"

# Building up file paths one step at a time (if any ever need to be printed in the future)
rawDocumentFilePathContextBase = "".join([rawDocumentFilePathBase, fileContext, "/"])
rawDocumentFilePathString = "".join([rawDocumentFilePathContextBase, fileName, ".pdf"])
rawDocumentFilePath = Path(rawDocumentFilePathString)

destinationFilePathBase = "/mnt/nvme0n1/database/storage/readReadyDocuments/"
destinationFilePathString = "".join([destinationFilePathBase, fileContext, "/", fileName, ".txt"])
destinationFilePath = Path(destinationFilePathString)

# ----------------------------------------
#   Fetch from rawDocuments (Move from downloads to storage/rawDocuments if necessary)
# ----------------------------------------

if(not rawDocumentFilePath.is_file()):
    # See if file name exists in downloads folder. If not, the fileName argument may be incorrect
    downloadFilePathString = "".join([downloadFilePathBase, fileName, ".pdf"])
    downloadFilePath = Path(downloadFilePathString)
    if(not downloadFilePath.is_file()):
        # There is nothing to find. Terminate
        print("File name " + fileName + " does not exist in " + rawDocumentFilePathContextBase + " nor " + downloadFilePathBase)
        sys.exit();

    shutil.copy(downloadFilePathString, rawDocumentFilePathContextBase)

# ----------------------------------------
#   Read pdf and save as text document
# ----------------------------------------

reader = PdfReader(rawDocumentFilePath)
pageCount = len(reader.pages)

with open(destinationFilePath, "w", encoding="utf-8") as textFile:
    for pageNum, page in enumerate(reader.pages):
        text = page.extract_text()

        if text:
            textFile.write(text)
            textFile.write("\n\n") # Separator between pages

print("Output saved to " + destinationFilePathString)
