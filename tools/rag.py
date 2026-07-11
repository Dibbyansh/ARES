# RAG knowledge base — stores and searches emergency guidelines via ChromaDB
import chromadb

# Persistent vector store on disk
chroma_client = chromadb.PersistentClient(path="./chroma_db")

knowledge_collection = chroma_client.get_or_create_collection(name="emergency_guidelines")


def load_knowledge_base():
    """Index guidelines from docs.txt into ChromaDB."""
    
    try:
        with open("docs.txt", "r", encoding="utf-8") as file:
            lines = [line.strip() for line in file if line.strip()]
        
        if not lines:
            print("⚠️  docs.txt is empty - no guidelines to load!")
            return
        
        # Embed and store each guideline line
        knowledge_collection.add(
            documents=lines,
            ids=[str(i) for i in range(len(lines))]
        )
        
        print(f"✓ Loaded {len(lines)} guidelines into knowledge base")
        
    except FileNotFoundError:
        print("⚠️  docs.txt not found - please create it with emergency guidelines")
    except Exception as error:
        print(f"❌ Error loading knowledge base: {error}")


def search_guidelines(query, max_results=5):
    """Semantic search for guidelines matching the query."""
    
    if knowledge_collection.count() == 0:
        return ""
    
    try:
        # Semantic similarity search against stored guidelines
        results = knowledge_collection.query(
            query_texts=[query],
            n_results=min(max_results, knowledge_collection.count())
        )
        
        documents = results.get("documents", [[]])[0]
        
        return "\n".join(documents)
        
    except Exception as error:
        print(f"⚠️  Error searching knowledge base: {error}")
        return ""


def knowledge_base_count():
    """Return number of indexed guidelines."""
    return knowledge_collection.count()
