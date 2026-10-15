import chromadb

client = chromadb.PersistentClient(path='/mnt/nvme0n1/database/storage/chromadb')

from chromadb.utils.embedding_functions import DefaultEmbeddingFunction

client.delete_collection(name="my_collection")

collection = client.create_collection(
    name="my_collection",
    embedding_function=DefaultEmbeddingFunction()
    )

default_ef = DefaultEmbeddingFunction()
embeddings = default_ef(["Yeah hi its me"])
print(embeddings)

collection.query(query_embeddings=embeddings)
