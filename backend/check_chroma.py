import chromadb

client = chromadb.PersistentClient(path="./chroma_data")
collection = client.get_or_create_collection(name="conversations")

print(f"Count: {collection.count()}")
results = collection.get()
print("Documents:")
for doc in results['documents']:
    print(doc)
