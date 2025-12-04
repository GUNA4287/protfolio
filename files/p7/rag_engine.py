import faiss
import openai
from sentence_transformers import SentenceTransformer
import numpy as np
import os

# Load embedding model (only once)
embedder = SentenceTransformer("all-MiniLM-L6-v2")

# Example documents (later you can load from file/db)
docs = [
    "Hidan IT provides website development.",
    "Hidan IT offers mobile app development.",
    "Hidan IT delivers freelance IT solutions.",
    "Hidan IT builds AI chatbots."
]

# Convert docs → vectors
doc_vectors = embedder.encode(docs)
dimension = doc_vectors.shape[1]

# Build FAISS index
index = faiss.IndexFlatL2(dimension)
index.add(np.array(doc_vectors))

def ask_question(query: str) -> str:
    """Retrieve relevant docs and ask GPT."""
    # Step 1: Embed query
    q_vec = embedder.encode([query])

    # Step 2: Search top docs
    distances, indices = index.search(np.array(q_vec), k=2)
    retrieved_docs = [docs[i] for i in indices[0]]

    # Step 3: Build GPT prompt
    context = "\n".join(retrieved_docs)
    prompt = f"Answer the question using the following context:\n{context}\n\nQuestion: {query}"

    # Step 4: Call GPT
    openai.api_key = os.getenv("OPENAI_API_KEY")  # use .env
    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "system", "content": "You are Hidan, a helpful AI assistant."},
            {"role": "user", "content": prompt},
        ],
    )
    return response.choices[0].message["content"]
