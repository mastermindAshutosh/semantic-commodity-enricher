# src/vector_engine.py
import faiss
import numpy as np
import pickle
from sentence_transformers import SentenceTransformer

class VectorEngine:
    def __init__(self, model_name='all-MiniLM-L6-v2'):
        self.model = SentenceTransformer(model_name)
        self.dimension = 384  # Dimension for all-MiniLM-L6-v2
        self.index = faiss.IndexFlatL2(self.dimension)
        self.metadata_store = [] # Simple list to map index ID to metadata

    def vectorize_text(self, text):
        return self.model.encode([text])[0]

    def add_to_index(self, text, metadata):
        """
        Adds vector to FAISS and metadata to local store.
        """
        vector = self.vectorize_text(text)
        # FAISS expects float32
        vector = np.array([vector], dtype='float32')
        self.index.add(vector)
        self.metadata_store.append(metadata)

    def search(self, query_text, k=3):
        """
        Fuzzy search for commodity.
        """
        vector = self.vectorize_text(query_text)
        vector = np.array([vector], dtype='float32')
        
        distances, indices = self.index.search(vector, k)
        
        results = []
        for i, idx in enumerate(indices[0]):
            if idx != -1:
                results.append({
                    "metadata": self.metadata_store[idx],
                    "score": float(distances[0][i])
                })
        return results

    def save_index(self, path_prefix="data/output/vector_store"):
        faiss.write_index(self.index, f"{path_prefix}.index")
        with open(f"{path_prefix}_meta.pkl", "wb") as f:
            pickle.dump(self.metadata_store, f)