# Christian Caillouet - 10/15/2026

import os
import sys
import subprocess
import chromadb
import ollama

import logging
from datetime import datetime

# -------------------------------
#       SETTINGS
# -------------------------------
logPath = "/mnt/nvme0n1/database/logs/"

collectionQueryResultCount = 8
#baseAiPrompt = "The question is: \"{}\", and the document excerpts are as follows: {}"

modelFile = '''
FROM llama3.2
PARAMETER temperature 1

SYSTEM You are a personal advisor for a professor at SLU. You'll be given a question and some policy document excerpts relevant to the question. Answer the question with the information provided in the excerpts, prioritizing accuracy and clarity. Explain your conclusions thoroughly and avoid repeating yourself.'
'''

# experiment with switching question and excerpt order
client = chromadb.PersistentClient(path='/mnt/nvme0n1/database/storage/chromadb')
collection = client.get_collection(name = "Pocket_Lawyer")

# AI
longAns = False
if longAns:
    model = "gemma4:e4b"
else:
    model = "qwen2.5:0.5b"

# -------------------------------
#      SETUP
# -------------------------------
messages = []
terminated = False

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
#       FUNCTIONS
# -------------------------------
def getUserInput(prompt):
    userInput = input("Ask me anything: ")
    logger.info("Input recieved: " + userInput)

    messages.append({
        'role': 'user',
        'content': userInput
        })

    return userInput

def getChromaResults(prompt):
    results = collection.query(
        query_texts = [userPrompt],
        n_results = collectionQueryResultCount
    )

    logger.debug("Chroma query output: " + str(results) + "\n")


    return results


def formatChromaResults(results):
    documents = results["documents"]
    output = ""

    i = 0
    for doc in documents:
        i += 1
        output = output + (str(i) + " - " + str(doc) + "\n")


    messages.append({
        'role': 'system',
        'content': output
        })


#def formatAIPrompt(prompt, chromaOutput):
    #aiPrompt = baseAiPrompt.format(userPrompt, chromaOutput["documents"])

    #logger.debug("AI prompt: " + aiPrompt + "\n")

 #   return aiPrompt

def collectSources(chromaOutput):
    sources = []

    for metadata in chromaOutput["metadatas"]:
        for entry in metadata:
            if [entry["docName"], entry["docSource"]] not in sources:
                sources.append([entry["docName"], entry["docSource"]])

    return sources

def streamAIResponse(model):
    response = "";

    stream = ollama.chat(model=model, messages=messages, stream=True)
    for chunk in stream:
        response = response + chunk['message']['content']
        print(chunk['message']['content'], end='', flush=True)

    messages.append({
        'role': 'assisstant',
        'content': response
        })
    logger.debug("AI Response: " + response)


# -------------------------------
#       PROGRAM LOOP
# -------------------------------
logger.info("AskQwen Start")
print("Starting OPPL - Type .exit to terminate")
print("Hi! I'm the Orange Pi Pocket Lawyer!")
while not terminated:
    userPrompt = getUserInput("Ask me anything: ")



    if ".exit" in userPrompt:
        logger.info("Exit command received")
        terminated = True
        continue

    print("Thinking... ")


    chromaResults = getChromaResults(userPrompt)
    formatChromaResults(chromaResults)

    # Collect sources for display later
    sources = collectSources(chromaResults)

    # Make AI do work
    streamAIResponse(model)

    print("\n")
    if sources:
        i = 0
        print("Sources referenced: ")
        for source in sources:
            i += 1
            print(str(i) + ") " + source[0] + ": " + source[1])
        print("\n")

print("Ending Orange Pi Pocket Lawyer - See you later!")
logger.info("AskQwen End")
