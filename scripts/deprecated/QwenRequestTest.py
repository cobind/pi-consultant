import subprocess
import chromadb

# Creates our DB/ connects to our existing DB
chroma_client = chromadb.Client()
client = chromadb.PersistentClient(path='/mnt/nvme0n1/database/storage/chromadb')
collection = client.get_or_create_collection(name = "Pocket_Lawyer")

# -- Ok this needs to happen after the prompt is recieved probably
# -------------------------------------------------

collection.upsert(
    ids=["test_blue_001", "test_red_001", "test_green_001"],
    documents=[
        "All water is blue.",
        "The car is red.",
        "The tree is green."
        ]
    )

file_path = "/mnt/nvme0n1/database/storage/readReadyDocuments/sluPolicy/confidentiality.txt"

with open(file_path, "r", encoding="utf-8") as file:
    text = file.read()

collection.upsert(ids=["slu_comfidentiality_001"],
                  documents=[text],
                  metadatas=[{"source": "confidentiality.txt"}]
                  )

# -------------------------------------------------

print("Totalrecords:", collection.count())
print(collection.peek(limit=10)["documents"])

userPrompt = input("enter your qwen prompt \n")

results = collection.query(
    query_texts=[userPrompt],
    n_results=1
    )


prompt = "Use the context in brackets to answer the question in quotes." + str(results.get("documents")) + "\"" + userPrompt + "\""

answer = subprocess.run(
    ["ollama", "run", "qwen2.5:0.5b", prompt],
                        capture_output=True,
                         text=True,
                         check=True
                         )

#print (results.get("documents"))
print(answer.stdout)
