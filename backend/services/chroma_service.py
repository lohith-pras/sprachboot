import chromadb
import os
import uuid

# Initialize the Chroma client. Path is overridable via CHROMA_PERSIST_DIR so a
# Docker volume can persist memory outside the image (defaults to local dir).
chroma_client = chromadb.PersistentClient(
    path=os.getenv("CHROMA_PERSIST_DIR", "./chroma_data")
)
collection = chroma_client.get_or_create_collection(name="conversations")

def add_turn_to_memory(session_id: int, user_input: str, ai_response: str):
    """Save a conversation turn to ChromaDB."""
    # We use a combined text as the document so it can be matched against future user inputs
    document = f"User: {user_input}\nAI: {ai_response}"
    metadata = {"session_id": session_id}
    doc_id = str(uuid.uuid4())
    
    collection.add(
        documents=[document],
        metadatas=[metadata],
        ids=[doc_id]
    )

def get_relevant_context(user_input: str, limit: int = 3) -> str:
    """Retrieve the most relevant past conversation turns."""
    try:
        # Check if collection is empty
        if collection.count() == 0:
            return ""
            
        results = collection.query(
            query_texts=[user_input],
            n_results=min(limit, collection.count())
        )
        if results and results['documents'] and results['documents'][0]:
            # join the documents
            return "\n\n".join(results['documents'][0])
    except Exception as e:
        print(f"ChromaDB query error: {e}")
        
    return ""
