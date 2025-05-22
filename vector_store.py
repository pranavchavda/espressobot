import numpy as np
from sklearn.metrics.pairwise import cosine_similarity
import logging
from collections import defaultdict

logger = logging.getLogger(__name__)

class VectorStore:
    _instance = None
    _embeddings_data = None # Will be defaultdict(lambda: {'keys': [], 'vectors': []})

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(VectorStore, cls).__new__(cls)
            cls._embeddings_data = defaultdict(lambda: {'keys': [], 'vectors': []})
            logger.info("In-memory VectorStore initialized.")
        return cls._instance

    def add_embedding(self, user_id: str, memory_key: str, embedding: list[float]):
        """Adds an embedding for a specific user and memory key."""
        if not user_id or not memory_key or not embedding:
            logger.warning(f"VectorStore: Invalid input for add_embedding. user_id='{user_id}', memory_key='{memory_key}', embedding_present={bool(embedding)}")
            return

        user_store = self._embeddings_data[user_id]
        
        # Check if memory_key already exists for this user and update if so
        if memory_key in user_store['keys']:
            idx = user_store['keys'].index(memory_key)
            user_store['vectors'][idx] = np.array(embedding, dtype=np.float32)
            logger.info(f"VectorStore: Updated embedding for user '{user_id}', key '{memory_key}'.")
        else:
            user_store['keys'].append(memory_key)
            user_store['vectors'].append(np.array(embedding, dtype=np.float32))
            logger.info(f"VectorStore: Added new embedding for user '{user_id}', key '{memory_key}'.")

    def find_similar_embeddings(self, user_id: str, query_embedding: list[float], top_n: int = 3) -> list[tuple[str, float]]:
        """Finds the top_n most similar memory keys and their similarity scores for a given user."""
        if not user_id or not query_embedding:
            logger.warning(f"VectorStore: Invalid input for find_similar_embeddings. user_id='{user_id}', query_embedding_present={bool(query_embedding)}")
            return []

        user_store = self._embeddings_data.get(user_id)
        if not user_store or not user_store['vectors']:
            logger.info(f"VectorStore: No embeddings found for user '{user_id}'.")
            return []

        query_vec = np.array(query_embedding, dtype=np.float32).reshape(1, -1)
        stored_vectors_matrix = np.array(user_store['vectors'], dtype=np.float32)

        if stored_vectors_matrix.ndim == 1: # Single stored vector
            stored_vectors_matrix = stored_vectors_matrix.reshape(1, -1)
        
        if query_vec.shape[1] != stored_vectors_matrix.shape[1]:
            logger.error(f"VectorStore: Query embedding dimension ({query_vec.shape[1]}) does not match stored vectors dimension ({stored_vectors_matrix.shape[1]}) for user '{user_id}'.")
            return []

        try:
            similarities = cosine_similarity(query_vec, stored_vectors_matrix)[0]
        except Exception as e:
            logger.error(f"VectorStore: Error calculating cosine similarity for user '{user_id}': {e}", exc_info=True)
            return []

        # Pair keys with their similarity scores
        scored_keys = list(zip(user_store['keys'], similarities))

        # Sort by similarity score in descending order
        scored_keys.sort(key=lambda x: x[1], reverse=True)

        return scored_keys[:top_n]

    def delete_embedding(self, user_id: str, memory_key: str) -> bool:
        """Removes an embedding associated with a user and memory key. Returns True if successful."""
        if not user_id or not memory_key:
            logger.warning(f"VectorStore: Invalid input for delete_embedding. user_id='{user_id}', memory_key='{memory_key}'")
            return False

        user_store = self._embeddings_data.get(user_id)
        if not user_store or memory_key not in user_store['keys']:
            logger.info(f"VectorStore: Embedding not found for user '{user_id}', key '{memory_key}'. Cannot delete.")
            return False

        try:
            idx = user_store['keys'].index(memory_key)
            user_store['keys'].pop(idx)
            user_store['vectors'].pop(idx)
            logger.info(f"VectorStore: Deleted embedding for user '{user_id}', key '{memory_key}'.")
            # If user has no more keys, remove user entry to keep _embeddings_data clean
            if not user_store['keys']:
                del self._embeddings_data[user_id]
                logger.info(f"VectorStore: Removed user '{user_id}' from store as they have no more embeddings.")
            return True
        except ValueError:
            # Should not happen if memory_key in user_store['keys'] check passed, but as a safeguard.
            logger.error(f"VectorStore: Inconsistency found for user '{user_id}', key '{memory_key}' during deletion.", exc_info=True)
            return False

    def get_user_memory_keys(self, user_id: str) -> list[str]:
        """Returns all memory keys for a given user."""
        if user_id in self._embeddings_data:
            return list(self._embeddings_data[user_id]['keys']) # Return a copy
        return []

    def get_all_data_for_user(self, user_id: str) -> dict | None:
        """Returns all stored data for a user (keys and vectors). For debugging/testing."""
        if user_id in self._embeddings_data:
            return {
                'keys': list(self._embeddings_data[user_id]['keys']),
                'vectors': [v.tolist() for v in self._embeddings_data[user_id]['vectors']]
            }
        return None

# Example usage (optional, for testing):
if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)

    # Import EmbeddingService for testing
    from embedding_service import EmbeddingService
    embed_service = EmbeddingService()

    if not embed_service._model:
        print("Embedding model failed to load from EmbeddingService. Cannot run VectorStore tests.")
    else:
        vec_store = VectorStore()
        vec_store2 = VectorStore() # Should be the same instance
        print(f"VectorStore is a singleton: {vec_store is vec_store2}")

        user1 = "user_alpha"
        user2 = "user_beta"

        # Test adding embeddings
        mem1_u1_key = "meeting_notes_project_x"
        mem1_u1_text = "Project X kickoff meeting discussed budget and timelines."
        mem1_u1_emb = embed_service.get_embedding(mem1_u1_text)
        if mem1_u1_emb: vec_store.add_embedding(user1, mem1_u1_key, mem1_u1_emb)

        mem2_u1_key = "recipe_pasta_sauce"
        mem2_u1_text = "My favorite pasta sauce recipe includes tomatoes, basil, and garlic."
        mem2_u1_emb = embed_service.get_embedding(mem2_u1_text)
        if mem2_u1_emb: vec_store.add_embedding(user1, mem2_u1_key, mem2_u1_emb)
        
        # Update an embedding
        mem1_u1_text_updated = "Project X kickoff meeting confirmed budget is $50k and timeline is 3 months."
        mem1_u1_emb_updated = embed_service.get_embedding(mem1_u1_text_updated)
        if mem1_u1_emb_updated: vec_store.add_embedding(user1, mem1_u1_key, mem1_u1_emb_updated) # Re-adding same key updates

        mem1_u2_key = "travel_ideas_japan"
        mem1_u2_text = "Thinking of visiting Tokyo and Kyoto next spring."
        mem1_u2_emb = embed_service.get_embedding(mem1_u2_text)
        if mem1_u2_emb: vec_store.add_embedding(user2, mem1_u2_key, mem1_u2_emb)

        print(f"User1 keys: {vec_store.get_user_memory_keys(user1)}")
        print(f"User2 keys: {vec_store.get_user_memory_keys(user2)}")

        # Test finding similar embeddings
        query_u1_text = "What was discussed about Project X funding?"
        query_u1_emb = embed_service.get_embedding(query_u1_text)
        if query_u1_emb:
            similar_u1 = vec_store.find_similar_embeddings(user1, query_u1_emb, top_n=1)
            print(f"Similar to '{query_u1_text}' for {user1}: {similar_u1}")

        query_u2_text = "Places to see in Japan?"
        query_u2_emb = embed_service.get_embedding(query_u2_text)
        if query_u2_emb:
            similar_u2 = vec_store.find_similar_embeddings(user2, query_u2_emb, top_n=1)
            print(f"Similar to '{query_u2_text}' for {user2}: {similar_u2}")
        
        # Test finding with no embeddings for a user
        similar_no_user = vec_store.find_similar_embeddings("user_gamma", query_u1_emb, top_n=1)
        print(f"Similar for non-existent user 'user_gamma': {similar_no_user}")

        # Test deleting embeddings
        vec_store.delete_embedding(user1, mem2_u1_key)
        print(f"User1 keys after deleting '{mem2_u1_key}': {vec_store.get_user_memory_keys(user1)}")
        
        vec_store.delete_embedding(user1, mem1_u1_key) # Delete last key for user1
        print(f"User1 keys after deleting '{mem1_u1_key}': {vec_store.get_user_memory_keys(user1)}")
        print(f"User1 data after all keys deleted: {vec_store.get_all_data_for_user(user1)}")

        # Test deleting non-existent key
        vec_store.delete_embedding(user2, "non_existent_key")
        print(f"User2 keys after attempting to delete non-existent key: {vec_store.get_user_memory_keys(user2)}")
