# Christian Caillouet - 10/1/2026

import os
import sys
import subprocess
import chromadb

import logging
from datetime import datetime

# -------------------------------
#       SETTINGS
# -------------------------------
logPath = "/mnt/nvme0n1/database/logs/"

collectionQueryResultCount = 8
baseAiPrompt = "You are a personal advisor. Using only the information in the relevant document excerpts below, answer the provided question with the best advice you may provide, prioritizing accuracy, clarity, and thoroughness. Explain your conclusions thoroughly and avoid repeating yourself. The question is: \"{}\", and the document excerpts are as follows: {}"

# experiment with switching question and excerpt order

# -------------------------------
#       SETUP
# -------------------------------
# AI
client = chromadb.PersistentClient(path='/mnt/nvme0n1/database/storage/chromadb')
collection = client.get_collection(name = "Pocket_Lawyer")
terminated = False
longAns = False
if longAns:
    model = "gemma4:e4b"
else:
    model = "qwen2.5:0.5b"

# Logger
now = datetime.now()
nowStr = now.strftime("%m%d%Y-%H%M")
logFileName = logPath + "AskQwen-" + nowStr + ".log"
logging.basicConfig(
    filename=logFileName,
    format='%(asctime)s %(levelname)s: %(message)s',
    filemode='w'
    )
logger = logging.getLogger()
logger.setLevel(logging.DEBUG)

# -------------------------------
#       PROGRAM LOOP
# -------------------------------
logger.info("AskQwen Start")
print("Starting Orange Pi Pocket Lawyer - Type .exit to terminate")
while not terminated:
    print("Hi! I'm the Orange Pi Pocket Lawyer!")
    userPrompt = input("Ask me anything: ")

    if ".exit" in userPrompt:
        logger.info("Exit command received")
        terminated = True
        continue

    logger.info("Input recieved: " + userPrompt)

    chromaResults = collection.query(
        query_texts = [userPrompt],
        n_results = collectionQueryResultCount
    )

    logger.debug("Chroma query output: " + str(chromaResults) + "\n")

    aiPrompt = baseAiPrompt.format(userPrompt, chromaResults["documents"])
    logger.debug("AI prompt: " + aiPrompt + "\n")

    # Collect sources for display later
    sources = []
    for metadata in chromaResults["metadatas"]:
        for entry in metadata:
            if [entry["docName"], entry["docSource"]] not in sources:
                sources.append([entry["docName"], entry["docSource"]])

    # Make AI do work
    print("Thinking... Please allow me a few minutes to answer.")
    logger.info("AI Started")

    answer = subprocess.run(
       ["ollama", "run", model],
       input=aiPrompt,
       capture_output=True,
       text=True,
       check=True
    )

    logger.info("AI Finished\n")
    print("\n")

    # Print output and sources
    print(answer.stdout)
    logger.info("Output: " + str(answer.stdout))

    if sources:
        i = 0
        print("Sources referenced: ")
        for source in sources:
            i += 1
            print(str(i) + ") " + source[0] + ": " + source[1])
        print("\n")

print("Ending Orange Pi Pocket Lawyer - See you later!")
logger.info("AskQwen End")
