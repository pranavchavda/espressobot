# from sentence_transformers import SentenceTransformer
import openai
import os
import logging

logger = logging.getLogger(__name__)

class EmbeddingService:
    _instance = None
    # _model = None # For sentence-transformers
    _client = None # For OpenAI
    _openai_model_name = None # For OpenAI

    def __new__(cls, model_name: str = 'text-embedding-3-small', use_openai: bool = True):
        if cls._instance is None:
            cls._instance = super(EmbeddingService, cls).__new__(cls)
            if use_openai:
                logger.info(f"Initializing OpenAI client for embeddings with model: {model_name}")
                if not os.getenv("OPENAI_API_KEY"):
                    logger.error("OPENAI_API_KEY environment variable not set. OpenAI embeddings will not work.")
                    cls._client = None
                else:
                    try:
                        cls._client = openai.OpenAI()
                        cls._openai_model_name = model_name
                        logger.info(f"OpenAI client initialized successfully for model '{model_name}'.")
                    except Exception as e:
                        logger.error(f"Failed to initialize OpenAI client: {e}", exc_info=True)
                        cls._client = None
            # else:
            #     # Original sentence-transformers logic (commented out)
            #     try:
            #         logger.info(f"Loading local embedding model: {model_name}")
            #         cls._model = SentenceTransformer(model_name)
            #         logger.info(f"Local embedding model '{model_name}' loaded successfully.")
            #     except Exception as e:
            #         logger.error(f"Failed to load local embedding model '{model_name}': {e}", exc_info=True)
            #         cls._model = None
        return cls._instance

    def get_embedding(self, text: str) -> list[float] | None:
        """Generates an embedding for the given text."""
        if self._client and self._openai_model_name:
            # OpenAI implementation
            if not text or not isinstance(text, str):
                logger.warning("Invalid input text for OpenAI embedding. Must be a non-empty string.")
                return None
            try:
                # OpenAI API recommends replacing newlines with a space.
                processed_text = text.replace("\n", " ") 
                response = self._client.embeddings.create(
                    model=self._openai_model_name,
                    input=[processed_text] # API expects a list of texts
                )
                return response.data[0].embedding
            except Exception as e:
                logger.error(f"Error generating OpenAI embedding for text '{text[:50]}...': {e}", exc_info=True)
                return None
        # elif self._model:
        #     # Original sentence-transformers implementation (commented out)
        #     if not text or not isinstance(text, str):
        #         logger.warning("Invalid input text for local embedding. Must be a non-empty string.")
        #         return None
        #     try:
        #         embedding = self._model.encode(text, convert_to_tensor=False) # Get numpy array
        #         return embedding.tolist() # Convert to list of floats
        #     except Exception as e:
        #         logger.error(f"Error generating local embedding for text '{text[:50]}...': {e}", exc_info=True)
        #         return None
        else:
            logger.error("Embedding service (OpenAI client or local model) is not properly initialized. Cannot generate embedding.")
            return None

    def get_embeddings_batch(self, texts: list[str], batch_size: int = 2048) -> list[list[float] | None]:
        """Generates embeddings for a batch of texts using OpenAI."""
        if not self._client or not self._openai_model_name:
            logger.error("OpenAI client is not initialized. Cannot generate batch embeddings.")
            return [None] * len(texts)
        
        if not texts:
            return []

        all_embeddings: list[list[float] | None] = [None] * len(texts)
        original_indices = list(range(len(texts)))

        # Filter out invalid texts and keep track of their original positions
        valid_texts_with_indices = []
        for i, text in enumerate(texts):
            if text and isinstance(text, str):
                valid_texts_with_indices.append((text.replace("\n", " "), i))
            else:
                logger.warning(f"Invalid input text at index {i} in batch. Will be skipped.")

        if not valid_texts_with_indices:
            logger.warning("No valid texts found in the batch.")
            return all_embeddings

        processed_texts = [item[0] for item in valid_texts_with_indices]
        original_valid_indices = [item[1] for item in valid_texts_with_indices]

        for i in range(0, len(processed_texts), batch_size):
            batch_texts = processed_texts[i:i + batch_size]
            batch_original_indices = original_valid_indices[i:i + batch_size]
            
            try:
                response = self._client.embeddings.create(
                    model=self._openai_model_name,
                    input=batch_texts
                )
                # OpenAI API returns embeddings in the same order as the input batch
                for j, embedding_data in enumerate(response.data):
                    original_idx = batch_original_indices[j]
                    all_embeddings[original_idx] = embedding_data.embedding
            except Exception as e:
                logger.error(f"Error generating OpenAI embeddings for batch (indices {batch_original_indices[0]}-{batch_original_indices[-1]}): {e}", exc_info=True)
                # For failed batch, mark corresponding embeddings as None
                for original_idx in batch_original_indices:
                    all_embeddings[original_idx] = None
        
        return all_embeddings

# Example usage (optional, for testing):
if __name__ == '__main__':
    # Configure basic logging for testing
    logging.basicConfig(level=logging.INFO)
    
    # Test service instantiation and model loading
    service1 = EmbeddingService()
    service2 = EmbeddingService() # Should return the same instance

    print(f"Service1 is Service2: {service1 is service2}")

    if service1._client: # Check for OpenAI client for testing
        # Test single embedding generation
        print("\n--- Testing Single Embeddings ---")
        text1 = "This is a test sentence."
        embedding1 = service1.get_embedding(text1)
        if embedding1:
            print(f"Embedding for '{text1}': {embedding1[:5]}... (length: {len(embedding1)})")

        text2 = "Another example sentence for semantic comparison."
        embedding2 = service1.get_embedding(text2)
        if embedding2:
            print(f"Embedding for '{text2}': {embedding2[:5]}... (length: {len(embedding2)})")
        
        # Test invalid single input
        invalid_embedding = service1.get_embedding("")
        print(f"Embedding for empty string: {invalid_embedding}")

        invalid_embedding_type = service1.get_embedding(123)
        print(f"Embedding for non-string input: {invalid_embedding_type}")

        # Test batch embedding generation
        print("\n--- Testing Batch Embeddings ---")
        texts_for_batch = [
            "First sentence for batch processing.",
            "Second sentence, also for the batch.",
            "", # Empty string test
            "A third valid sentence.",
            12345, # Invalid type test
            "Yet another one to make the list longer and test batching logic if limit is small."
        ]
        batch_embeddings = service1.get_embeddings_batch(texts_for_batch)
        
        print(f"Requested {len(texts_for_batch)} batch embeddings, received {len(batch_embeddings)} results.")
        for i, (text, emb) in enumerate(zip(texts_for_batch, batch_embeddings)):
            if emb:
                print(f"Batch item {i} ('{str(text)[:30]}...'): {emb[:5]}... (length: {len(emb)})")
            else:
                print(f"Batch item {i} ('{str(text)[:30]}...'): Failed or invalid input")

        # Test with a larger batch that might exceed a hypothetical small batch_size for testing chunking
        # (default batch_size is 2048, so this won't trigger chunking unless manually set lower in a test)
        print("\n--- Testing Batch Embeddings (Small Batch Size Scenario) ---")
        # To test chunking, you would call like: service1.get_embeddings_batch(many_texts, batch_size=2)
        small_batch_test_texts = ["text1", "text2", "text3", "text4", "text5"]
        # Simulate calling with a small batch size for demonstration of logic
        # In real use, the default batch_size=2048 is used unless overridden.
        # We'll test the method with its default batch_size here.
        small_batch_embeddings = service1.get_embeddings_batch(small_batch_test_texts, batch_size=2) # Forcing small batch here
        print(f"Requested {len(small_batch_test_texts)} for small batch test, received {len(small_batch_embeddings)} results.")
        for i, (text, emb) in enumerate(zip(small_batch_test_texts, small_batch_embeddings)):
            if emb:
                print(f"Small batch item {i} ('{str(text)[:30]}...'): {emb[:5]}... (length: {len(emb)})")
            else:
                print(f"Small batch item {i} ('{str(text)[:30]}...'): Failed or invalid input")

    else:
        print("Embedding model failed to load. Cannot run embedding tests.")

    # Test with a different model name (will still use the first loaded model due to singleton pattern)
    # To truly test with a different model, you'd need to reset _instance and _client or change the pattern.
    # service_alt_model = EmbeddingService(model_name='text-embedding-ada-002') 
    # print(f"Service1 is Service_alt_model: {service1 is service_alt_model}") # Still True
